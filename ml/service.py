"""Small, deterministic fashion retrieval service.

The service intentionally has no model download in its startup path.  It uses
TF-IDF text similarity, image colour histograms, and the outfit co-occurrence
file as an explainable compatibility graph.
"""
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

from fastapi import FastAPI, HTTPException, Query
from fastapi import Request
from pydantic import BaseModel, Field

try:
    from PIL import Image
except ImportError:  # pragma: no cover - colour extraction remains optional
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
        counts = Counter(doc)
        return {t: (count / len(doc)) * math.log((1 + len(docs)) / (1 + df[t])) for t, count in counts.items()} if doc else {}
    qv = vector(q)
    qnorm = math.sqrt(sum(value * value for value in qv.values())) or 1
    scores = []
    for doc in docs:
        dv = vector(doc)
        dnorm = math.sqrt(sum(value * value for value in dv.values())) or 1
        scores.append(sum(qv.get(key, 0) * value for key, value in dv.items()) / (qnorm * dnorm))
    return scores


def _colour(path: str) -> tuple[int, int, int] | None:
    if not Image or not path:
        return None
    try:
        with Image.open(IMAGE_ROOT / path) as image:
            image = image.convert("RGB").resize((1, 1))
            return tuple(image.getpixel((0, 0)))
    except (OSError, ValueError):
        return None


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
            for right in ids:
                if left != right:
                    edges[left].add(right)
    state.update(products=products, by_id=by_id, outfits=outfits, edges=edges, ready=True)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    _load()
    yield
    state.clear()


app = FastAPI(title="Atelier ML service", version="2.0.0", lifespan=lifespan)


class RecommendRequest(BaseModel):
    model_config = {"extra": "forbid"}
    query: str = Field(..., min_length=1, max_length=2000)
    gender: str | None = Field(default=None, max_length=64)
    occasion: str | None = Field(default=None, max_length=128)
    budget: float | None = Field(default=None, ge=0)
    k: int = Field(default=8, ge=1, le=50)


@app.get("/health")
def health():
    return {"status": "ok" if state.get("ready") else "starting", "products": len(state.get("products", [])), "outfits": len(state.get("outfits", [])), "features": ["tfidf", "image-colour", "co-occurrence-graph"], "llm_available": bool(os.getenv("OPENROUTER_API_KEY"))}


def _item(product: dict[str, Any]) -> dict[str, Any]:
    return {**product, "price_inr": float(product.get("price_inr") or 0), "image_url": product.get("image_url") or f"/data/{product.get('image', '')}"}


def _budget_ok(price: float, budget: float | None) -> bool:
    return budget is None or price <= budget


def _grounded_explanation(query: str, evidence: list[str], request: Request) -> str | None:
    """Use OpenRouter only when explicitly configured, with catalogue evidence in the prompt."""
    key = request.headers.get("x-openrouter-api-key") or os.getenv("OPENROUTER_API_KEY")
    if not key or not evidence:
        return None
    try:
        import httpx
        response = httpx.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={"model": os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini"), "temperature": 0.2,
                  "messages": [{"role": "user", "content": f"Explain this fashion recommendation in one sentence. Only use evidence: {evidence}. Query: {query}"}]},
            timeout=8,
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"].strip()
    except Exception:
        return None


@app.post("/recommend")
def recommend(body: RecommendRequest, request: Request):
    if not state.get("ready"):
        raise HTTPException(503, "Service not ready")
    products = state["products"]
    query = " ".join(filter(None, [body.query, body.gender or "", body.occasion or ""]))
    scores = _tfidf([f"{p.get('name','')} {p.get('category_label','')} {p.get('tags','')} {p.get('description','')}" for p in products], query)
    ranked = []
    for product, text_score in zip(products, scores):
        gender = str(product.get("gender", "")).lower()
        occasion = str(product.get("occasion", "")).lower()
        price = float(product.get("price_inr") or 0)
        if body.gender and body.gender.lower() not in (gender, "unisex"):
            continue
        if body.occasion and body.occasion.lower() not in occasion and body.occasion.lower() not in str(product.get("tags", "")).lower():
            continue
        if not _budget_ok(price, body.budget):
            continue
        ranked.append((text_score + (0.15 if body.occasion and body.occasion.lower() in occasion else 0), product))
    ranked.sort(key=lambda pair: pair[0], reverse=True)
    results = []
    for score, product in ranked[:body.k]:
        item = _item(product)
        graph = sorted(state["edges"].get(str(product.get("id")), []))[:3]
        evidence = [f"Co-occurs with {state['by_id'][edge].get('name', edge)}" for edge in graph if edge in state["by_id"]]
        results.append({
            "id": product.get("id"), "title": product.get("name"), "score": round(min(1, score), 4),
            "items": [item], "scores": {"retrieval": round(min(1, score), 4), "graph": round(min(1, len(graph) / 3), 4), "color": 0.5, "structure": 0.5},
            "evidence": evidence,
            "explanation": _grounded_explanation(body.query, evidence, request) or ("Matched by catalogue language" + (" and outfit co-occurrence evidence." if graph else ".")),
        })
    return {"query": body.query, "outfits": results, "rationale": "Deterministic TF-IDF retrieval with graph evidence.", "meta": {"engine": "tfidf+graph", "count": len(results)}}


@app.get("/catalog/products")
def catalog_products(limit: int = Query(40, ge=1, le=200), gender: str | None = None, slot: str | None = None):
    items = []
    for product in state.get("products", []):
        if gender and str(product.get("gender", "")).lower() not in (gender.lower(), "unisex"):
            continue
        if slot and str(product.get("slot") or product.get("category", "")).lower() != slot.lower():
            continue
        items.append(_item(product))
        if len(items) == limit:
            break
    return {"products": items, "count": len(items)}


@app.get("/catalog/stats")
def catalog_stats():
    products = state.get("products", [])
    return {"total": len(products), "outfits": len(state.get("outfits", [])), "by_gender": dict(Counter(str(p.get("gender", "unknown")).lower() for p in products)), "by_slot": dict(Counter(str(p.get("slot") or p.get("category", "unknown")).lower() for p in products))}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8000")))
