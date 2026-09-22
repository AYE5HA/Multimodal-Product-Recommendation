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

try:
    from PIL import Image
except ImportError:  # pragma: no cover
    Image = None

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = Path(os.getenv("DATA_DIR", ROOT / "data"))
PROCESSED_DIR = Path(os.getenv("ARTIFACT_DIR", DATA_DIR / "processed"))
IMAGE_ROOT = DATA_DIR
state: dict[str, Any] = {}


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
    state.update(products=products, by_id=by_id, outfits=outfits, edges=edges, ready=True)


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
    item["image_url"] = product.get("image_url") or (f"/data/{product.get('image')}" if product.get("image") else None)
    return item


def _outfit_items(outfit: dict[str, Any]) -> list[dict[str, Any]]:
    ids = [outfit.get(key) for key in ("hero_id", "second_id", "layer_id", "footwear_id", "accessory_1_id", "accessory_2_id") if outfit.get(key)]
    return [_item(state["by_id"][item_id]) for item_id in ids if item_id in state["by_id"]]


def _matches(outfit: dict[str, Any], body: RecommendRequest, items: list[dict[str, Any]]) -> bool:
    if body.gender and str(outfit.get("gender", "")).lower() not in (body.gender.lower(), "unisex"):
        return False
    if body.occasion and body.occasion.lower() not in str(outfit.get("occasion", "")).lower():
        return False
    if body.budget is not None and sum(float(item.get("price_inr") or 0) for item in items) > body.budget:
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
    query = " ".join(filter(None, [body.query, body.gender or "", body.occasion or ""]))
    outfits = state["outfits"]
    rows = [" ".join(str(outfit.get(key, "")) for key in ("theme", "occasion", "palette", "stylist_rationale", "hero", "second", "layer", "footwear", "accessory_1", "accessory_2")) for outfit in outfits]
    retrieval_scores = _tfidf(rows, query)
    candidates: list[tuple[float, dict[str, Any], list[dict[str, Any]], list[str]]] = []
    for outfit, retrieval in zip(outfits, retrieval_scores):
        items = _outfit_items(outfit)
        if not _matches(outfit, body, items):
            continue
        ids = [str(item.get("id")) for item in items]
        graph_links = sum(len(state["edges"].get(item_id, set())) for item_id in ids)
        graph_score = min(1.0, graph_links / max(1, len(ids) * 3))
        occasion_score = 1.0 if body.occasion and body.occasion.lower() in str(outfit.get("occasion", "")).lower() else 0.5
        score = min(1.0, (retrieval * 0.60) + (graph_score * 0.25) + (occasion_score * 0.15))
        evidence = [f"Curated {outfit.get('occasion', 'occasion')} look: {outfit.get('theme', 'coordinated palette')}", f"Compatibility graph connects {len(ids)} catalog items", str(outfit.get("stylist_rationale", "")).strip()]
        candidates.append((score, outfit, items, [item for item in evidence if item]))
    candidates.sort(key=lambda item: item[0], reverse=True)
    results = []
    for score, outfit, items, evidence in candidates[: body.k]:
        graph_score = min(1.0, sum(len(state["edges"].get(str(item.get("id")), set())) for item in items) / max(1, len(items) * 3))
        explanation = await _grounded_explanation(body.query, evidence, request)
        results.append({"id": outfit.get("outfit_id"), "title": outfit.get("theme") or outfit.get("hero") or "Curated look", "score": round(score, 4), "items": items, "scores": {"retrieval": round(min(1.0, score / 0.85), 4), "graph": round(graph_score, 4), "color": 0.5, "structure": round(min(1.0, len(items) / 5), 4)}, "evidence": evidence, "explanation": explanation or str(outfit.get("stylist_rationale") or "Ranked from catalog similarity and item compatibility evidence."), "total_price_inr": round(sum(item["price_inr"] for item in items), 2)})
    return {"query": body.query, "outfits": results, "rationale": "Curated outfit graph retrieval with lexical matching and compatibility evidence.", "meta": {"engine": "tfidf+outfit-graph", "count": len(results), "catalog_size": len(state["products"])} }


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
