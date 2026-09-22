"""Explainable fashion retrieval and outfit ranking service."""
from __future__ import annotations

import csv
import json
import math
import os
import re
from collections import Counter, defaultdict
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query, Request
from pydantic import BaseModel, Field

from graph import build_graph, evidence_for
from intent import plan_intent
from embeddings import FashionClipIndex

try:
    from PIL import Image
except ImportError:  # pragma: no cover
    Image = None

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = Path(os.getenv("DATA_DIR", ROOT / "data"))
PROCESSED_DIR = Path(os.getenv("ARTIFACT_DIR", DATA_DIR / "processed"))
IMAGE_ROOT = DATA_DIR
state: dict[str, Any] = {}
_visual_cache: dict[str, tuple[int, int, int] | None] = {}
_COLOURS = {"black": (25, 25, 25), "white": (235, 235, 235), "blue": (45, 85, 150), "navy": (25, 45, 85), "red": (170, 45, 45), "maroon": (110, 35, 45), "green": (50, 110, 70), "pink": (210, 120, 150), "yellow": (210, 175, 45), "gold": (190, 150, 50), "beige": (190, 165, 125), "brown": (110, 75, 50), "grey": (125, 125, 125)}


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", (text or "").lower())


def _tfidf(rows: list[str], query: str) -> list[float]:
    docs = [_tokens(value) for value in rows]
    q = _tokens(query)
    if not q:
        return [0.0] * len(rows)
    df = Counter(token for doc in docs for token in set(doc))

    def vector(doc: list[str]) -> dict[str, float]:
        if not doc:
            return {}
        counts = Counter(doc)
        return {token: (count / len(doc)) * math.log((1 + len(docs)) / (1 + df[token])) for token, count in counts.items()}

    query_vector = vector(q)
    query_norm = math.sqrt(sum(value * value for value in query_vector.values())) or 1
    scores = []
    for doc in docs:
        doc_vector = vector(doc)
        doc_norm = math.sqrt(sum(value * value for value in doc_vector.values())) or 1
        scores.append(sum(query_vector.get(key, 0) * value for key, value in doc_vector.items()) / (query_norm * doc_norm))
    return scores


def _intent_query(query: str) -> tuple[str, set[str]]:
    """Expand colloquial style intent into catalog vocabulary."""
    lowered = query.lower()
    expansions: list[str] = []
    intents: set[str] = set()
    if any(term in lowered for term in ("desi", "ethnic", "traditional", "indian", "saree", "sari", "lehenga", "kurta", "sherwani")):
        expansions += ["desi ethnic traditional indian saree sari lehenga kurta sherwani festive"]
        intents.update(("wedding", "festive"))
    if any(term in lowered for term in ("wedding", "wedding guest", "baraat", "ceremony")):
        expansions += ["wedding guest festive ceremony ethnic traditional"]
        intents.update(("wedding", "festive"))
    if any(term in lowered for term in ("party", "dinner", "night out", "evening")):
        expansions += ["party evening celebration"]
        intents.add("party")
    if any(term in lowered for term in ("office", "work", "client", "business")):
        expansions += ["office work business formal"]
        intents.add("office")
    return " ".join([query, *expansions]), intents


def _load() -> None:
    processed = PROCESSED_DIR / "catalog.json"
    products = json.loads(processed.read_text(encoding="utf-8")) if processed.exists() else _read_csv(DATA_DIR / "products.csv")
    if isinstance(products, dict):
        products = list(products.values())
    outfits = _read_csv(DATA_DIR / "outfits.csv")
    by_id = {str(item.get("id")): item for item in products}
    edges: dict[str, set[str]] = defaultdict(set)
    for outfit in outfits:
        ids = [outfit.get(key) for key in ("hero_id", "second_id", "layer_id", "footwear_id", "accessory_1_id", "accessory_2_id") if outfit.get(key)]
        for left in ids:
            edges[left].update(right for right in ids if right != left)
    state.update(products=products, by_id=by_id, outfits=outfits, edges=edges, graph=build_graph(outfits), clip_index=FashionClipIndex(PROCESSED_DIR).load(), ready=True)


def _image_colour(path: str) -> tuple[int, int, int] | None:
    if not Image or not path:
        return None
    if path in _visual_cache:
        return _visual_cache[path]
    try:
        with Image.open(IMAGE_ROOT / path) as image:
            colour = tuple(image.convert("RGB").resize((1, 1)).getpixel((0, 0)))
    except (OSError, ValueError):
        colour = None
    _visual_cache[path] = colour
    return colour


def _visual_score(items: list[dict[str, Any]], query: str) -> float:
    requested = [_COLOURS[key] for key in _COLOURS if re.search(rf"\b{key}\b", query.lower())]
    if not requested:
        return 0.5
    distances = []
    for item in items:
        colour = _image_colour(str(item.get("image", "")))
        if colour:
            distances.append(min(math.sqrt(sum((left - right) ** 2 for left, right in zip(colour, target))) for target in requested) / 441)
    return max(0.0, 1.0 - (sum(distances) / len(distances))) if distances else 0.25


def _catalog_color_score(items: list[dict[str, Any]], colors: list[str]) -> float:
    if not colors:
        return 0.5
    matched = 0
    for item in items:
        text = " ".join(str(item.get(key, "")) for key in ("name", "category_label", "tags", "description", "base_colour", "palette")).lower()
        if any(re.search(rf"\b{re.escape(color)}\b", text) for color in colors):
            matched += 1
    return matched / max(1, len(items))


@asynccontextmanager
async def lifespan(_app: FastAPI):
    _load()
    yield
    state.clear()


app = FastAPI(title="Atelier recommendation service", version="3.0.0", lifespan=lifespan)


class RecommendRequest(BaseModel):
    model_config = {"extra": "forbid"}
    query: str = Field(..., min_length=1, max_length=2000)
    gender: str | None = Field(default=None, max_length=64)
    occasion: str | None = Field(default=None, max_length=128)
    budget: float | None = Field(default=None, ge=0)
    k: int = Field(default=8, ge=1, le=50)


@app.get("/health")
def health() -> dict[str, Any]:
    return {"status": "ok" if state.get("ready") else "starting", "products": len(state.get("products", [])), "outfits": len(state.get("outfits", [])), "features": ["tfidf", "outfit-compatibility-graph", "grounded-explanations"], "llm_available": bool(os.getenv("OPENROUTER_API_KEY"))}


def _item(product: dict[str, Any]) -> dict[str, Any]:
    item = dict(product)
    item["price_inr"] = float(product.get("price_inr") or 0)
    # Prefer the image shipped with the catalog. Older processed artifacts may
    # contain remote Kaggle URLs that are unavailable in the browser/container.
    item["image_url"] = f"/data/{product.get('image')}" if product.get("image") else product.get("image_url")
    return item


def _outfit_items(outfit: dict[str, Any]) -> list[dict[str, Any]]:
    ids = [outfit.get(key) for key in ("hero_id", "second_id", "layer_id", "footwear_id", "accessory_1_id", "accessory_2_id") if outfit.get(key)]
    return [_item(state["by_id"][item_id]) for item_id in ids if item_id in state["by_id"]]


def _occasion_fit(value: str, query: str) -> float:
    value = value.lower()
    query = query.lower()
    aliases = {
        "wedding": ("wedding", "festive", "ceremony", "desi", "ethnic"),
        "party": ("party", "dinner", "night", "evening", "celebration"),
        "formal": ("formal", "office", "work", "business", "client"),
        "casual": ("casual", "everyday", "weekend", "day out"),
        "travel": ("travel", "vacation", "holiday", "resort"),
    }
    if not query:
        return 0.5
    if query in value or any(term in value for term in aliases.get(query, (query,))):
        return 1.0
    return 0.25


def _intent_fit(value: str, intents: set[str]) -> float:
    if not intents:
        return 0.5
    value = value.lower()
    if any(intent in value for intent in intents):
        return 1.0
    if "wedding" in intents or "festive" in intents:
        return 1.0 if any(term in value for term in ("wedding", "festive", "party")) else 0.05
    return 0.15


def _matches(outfit: dict[str, Any], body: RecommendRequest, items: list[dict[str, Any]]) -> bool:
    if body.gender and str(outfit.get("gender", "")).lower() not in (body.gender.lower(), "unisex"):
        return False
    return bool(items)


async def _grounded_explanation(query: str, evidence: list[str], _request: Request) -> str | None:
    key = os.getenv("OPENROUTER_API_KEY")
    if not key or not evidence:
        return None
    try:
        import httpx

        prompt = "Explain this fashion look in one concise sentence. Use only the supplied evidence.\nQuery: " + query + "\nEvidence: " + "; ".join(evidence)
        async with httpx.AsyncClient(timeout=8) as client:
            response = await client.post("https://openrouter.ai/api/v1/chat/completions", headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json", "HTTP-Referer": os.getenv("APP_URL", "http://localhost:5173")}, json={"model": os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini"), "temperature": 0.2, "messages": [{"role": "user", "content": prompt}]})
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"].strip()
    except Exception:
        return None


@app.post("/recommend")
async def recommend(body: RecommendRequest, request: Request) -> dict[str, Any]:
    if not state.get("ready"):
        raise HTTPException(503, "Service not ready")
    plan = await plan_intent(body.query, body.gender, body.occasion, body.budget)
    query = plan.normalized_query
    intents = set(plan.intents)
    outfits = state["outfits"]
    clip_index: FashionClipIndex = state["clip_index"]
    clip_scores = clip_index.text_scores(query, list(state["by_id"])) if clip_index.available else {}
    rows = [" ".join(str(outfit.get(key, "")) for key in ("theme", "occasion", "palette", "stylist_rationale", "hero", "second", "layer", "footwear", "accessory_1", "accessory_2")) for outfit in outfits]
    retrieval_scores = _tfidf(rows, query)
    prepared = [(outfit, retrieval, _outfit_items(outfit)) for outfit, retrieval in zip(outfits, retrieval_scores)]
    color_feasible = not plan.colors or any(_catalog_color_score(items[:1], plan.colors) > 0 for outfit, _, items in prepared if _matches(outfit, body, items))
    candidates: list[tuple[float, dict[str, Any], list[dict[str, Any]], list[str]]] = []
    for outfit, retrieval, items in prepared:
        if not _matches(outfit, body, items):
            continue
        outfit_text = " ".join(str(outfit.get(key, "")) for key in ("theme", "occasion", "hero", "second", "layer", "footwear", "accessory_1", "accessory_2", "stylist_rationale")).lower()
        if ("traditional" in intents or "wedding" in intents) and not any(term in (outfit_text + " " + str(outfit.get("wear_type", "")).lower()) for term in ("wedding", "festive", "ethnic", "saree", "sari", "kurta", "lehenga", "sherwani", "anarkali", "banarasi")):
            continue
        if any(re.search(rf"\b{re.escape(term)}\b", outfit_text) for term in plan.negative_terms if term in ("wedding gown", "bridal gown")):
            continue
        catalog_color_score = _catalog_color_score(items, plan.colors)
        if plan.colors and color_feasible and _catalog_color_score(items[:1], plan.colors) == 0:
            continue
        if "formal" in intents and any(term in outfit_text for term in ("sports", "sport", "yoga", "gym", "activewear")):
            continue
        if "formal" in intents and not any(term in outfit_text for term in ("formal", "office", "work", "business", "blazer", "trouser", "shirt", "suit")):
            continue
        total_price = sum(float(item.get("price_inr") or 0) for item in items)
        ids = [str(item.get("id")) for item in items]
        graph_links = sum(len(state["edges"].get(item_id, set())) for item_id in ids)
        graph_score = min(1.0, graph_links / max(1, len(ids) * 3))
        semantic_score = sum(clip_scores.get(item_id, 0.0) for item_id in ids) / max(1, len(ids))
        semantic_score = max(0.0, min(1.0, (semantic_score + 1.0) / 2.0)) if clip_scores else retrieval
        occasion_score = max(_occasion_fit(str(outfit.get("occasion", "")), plan.occasion or ""), _intent_fit(str(outfit.get("occasion", "")), intents))
        if intents and ("wedding" in intents or "festive" in intents):
            occasion_score = _intent_fit(str(outfit.get("occasion", "")), intents)
        budget_score = 1.0 if body.budget is None else max(0.0, min(1.0, body.budget / max(total_price, body.budget)))
        visual_score = catalog_color_score if plan.colors else _visual_score(items, query)
        score = min(1.0, (retrieval * 0.25) + (semantic_score * 0.25) + (graph_score * 0.20) + (occasion_score * 0.20) + (budget_score * 0.05) + (visual_score * 0.05))
        evidence = [f"Curated {outfit.get('occasion', 'occasion')} look: {outfit.get('theme', 'coordinated palette')}", f"Compatibility graph connects {len(ids)} catalog items", f"Visual palette match: {visual_score:.0%}", f"Total look price ₹{total_price:,.0f}", str(outfit.get("stylist_rationale", "")).strip()]
        candidates.append((score, outfit, items, [item for item in evidence if item]))
    relaxed_constraints: list[str] = []
    if body.budget is not None:
        within_budget = [candidate for candidate in candidates if sum(float(item.get("price_inr") or 0) for item in candidate[2]) <= body.budget]
        if within_budget:
            candidates = within_budget
        else:
            relaxed_constraints.append("budget")
    candidates.sort(key=lambda item: item[0], reverse=True)
    results = []
    seen: set[tuple[str, ...]] = set()
    for score, outfit, items, evidence in candidates:
        signature = tuple(sorted(str(item.get("id")) for item in items))
        if signature in seen:
            continue
        seen.add(signature)
        if len(results) >= body.k:
            break
        graph_score = min(1.0, sum(len(state["edges"].get(str(item.get("id")), set())) for item in items) / max(1, len(items) * 3))
        explanation = await _grounded_explanation(body.query, evidence, request)
        visual_score = catalog_color_score if plan.colors else _visual_score(items, query)
        results.append({"id": outfit.get("outfit_id"), "title": outfit.get("theme") or outfit.get("hero") or "Curated look", "score": round(score, 4), "items": items, "scores": {"retrieval": round(min(1.0, retrieval_scores[outfits.index(outfit)]), 4), "graph": round(graph_score, 4), "color": round(visual_score, 4), "structure": round(min(1.0, len(items) / 5), 4)}, "evidence": evidence, "graph_evidence": evidence_for(items, state["graph"], outfit), "explanation": explanation or str(outfit.get("stylist_rationale") or "Ranked from catalog similarity and item compatibility evidence."), "total_price_inr": round(sum(item["price_inr"] for item in items), 2)})
    return {"query": body.query, "query_plan": plan.as_dict(), "outfits": results, "rationale": "Multimodal intent planning with FashionCLIP retrieval and typed outfit-graph evidence.", "meta": {"engine": "intent+tfidf+fashionclip+outfit-graph", "count": len(results), "catalog_size": len(state["products"]), "embedding_index": clip_index.available, "relaxed_constraints": relaxed_constraints} }


@app.get("/catalog/products")
def catalog_products(limit: int = Query(40, ge=1, le=200), gender: str | None = None, slot: str | None = None) -> dict[str, Any]:
    items = []
    for product in state.get("products", []):
        if gender and str(product.get("gender", "")).lower() not in (gender.lower(), "unisex"):
            continue
        product_slot = str(product.get("slot") or product.get("category", "")).lower()
        if slot and slot.lower() not in product_slot:
            continue
        items.append(_item(product))
        if len(items) == limit:
            break
    return {"products": items, "count": len(items)}


@app.get("/catalog/stats")
def catalog_stats() -> dict[str, Any]:
    products = state.get("products", [])
    return {"total": len(products), "outfits": len(state.get("outfits", [])), "by_gender": dict(Counter(str(p.get("gender", "unknown")).lower() for p in products)), "by_slot": dict(Counter(str(p.get("slot") or p.get("category", "unknown")).lower() for p in products))}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8000")))
