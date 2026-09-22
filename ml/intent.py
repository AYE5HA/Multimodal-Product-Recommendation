"""Structured fashion intent extraction with an optional OpenRouter planner."""
from __future__ import annotations

import json
import os
import re
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class QueryIntent:
    raw_query: str
    normalized_query: str
    positive_terms: list[str] = field(default_factory=list)
    negative_terms: list[str] = field(default_factory=list)
    intents: list[str] = field(default_factory=list)
    occasion: str | None = None
    audience: str | None = None
    budget: float | None = None
    colors: list[str] = field(default_factory=list)
    source: str = "rules"
    confidence: float = 0.55

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _rule_plan(query: str, gender: str | None, occasion: str | None, budget: float | None) -> QueryIntent:
    text = query.lower().strip()
    positive = [token for token in re.findall(r"[a-z0-9]+", text) if len(token) > 2]
    negative: list[str] = []
    intents: list[str] = []
    colors = [color for color in ("black", "white", "blue", "navy", "red", "maroon", "green", "pink", "yellow", "gold", "beige", "brown", "grey", "purple", "cream") if re.search(rf"\b{color}\b", text)]
    if re.search(r"\bnot (the )?bride\b|\bnot bridal\b|\bguest\b", text):
        negative += ["bridal", "bride", "wedding gown"]
        intents.append("wedding_guest")
    if any(term in text for term in ("desi", "ethnic", "traditional", "indian", "saree", "sari", "lehenga", "kurta", "sherwani")):
        positive += ["desi", "ethnic", "traditional", "indian", "festive", "wedding"]
        intents.append("traditional")
    if any(term in text for term in ("wedding", "baraat", "ceremony")):
        intents.append("wedding")
    if any(term in text for term in ("party", "dinner", "night", "evening")):
        intents.append("party")
    if any(term in text for term in ("office", "work", "client", "business", "formal")):
        intents.append("formal")
    if any(term in text for term in ("casual", "everyday", "weekend")):
        intents.append("casual")
    if gender:
        positive.append(gender.lower())
    if occasion:
        positive.append(occasion.lower())
    if "wedding" in intents or "traditional" in intents:
        occasion = "wedding"
    return QueryIntent(query, " ".join(dict.fromkeys(positive)), list(dict.fromkeys(positive)), negative, list(dict.fromkeys(intents)), occasion, gender, budget, colors=colors)


async def plan_intent(query: str, gender: str | None = None, occasion: str | None = None, budget: float | None = None) -> QueryIntent:
    fallback = _rule_plan(query, gender, occasion, budget)
    key = os.getenv("OPENROUTER_API_KEY")
    if not key:
        return fallback
    try:
        import httpx

        system = """You are a fashion search query planner. Return only JSON with keys:
positive_terms (array of strings), negative_terms (array of strings), intents (array),
occasion (string or null), audience (string or null), confidence (number 0..1).
Interpret colloquial language. 'desi wedding guest, not bride' means traditional Indian
festive guestwear and must exclude bridalwear. Never invent products or claim availability."""
        async with httpx.AsyncClient(timeout=8) as client:
            response = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                json={"model": os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini"), "temperature": 0, "response_format": {"type": "json_object"}, "messages": [{"role": "system", "content": system}, {"role": "user", "content": json.dumps({"query": query, "gender": gender, "occasion": occasion, "budget": budget})}]},
            )
            response.raise_for_status()
            data = json.loads(response.json()["choices"][0]["message"]["content"])
            return QueryIntent(query, " ".join(data.get("positive_terms", [])), list(dict.fromkeys(data.get("positive_terms", []))), list(dict.fromkeys(data.get("negative_terms", []))), list(dict.fromkeys(data.get("intents", []))), data.get("occasion") or occasion, data.get("audience") or gender, budget, list(dict.fromkeys(data.get("colors", fallback.colors))), "openrouter", float(data.get("confidence", 0.8)))
    except Exception:
        return fallback
