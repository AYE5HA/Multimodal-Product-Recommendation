"""Evaluate recommendation contracts against a running ML service."""
from __future__ import annotations

import json
import os
import urllib.request
from pathlib import Path

BASE = os.getenv("ML_SERVICE_URL", "http://127.0.0.1:8000").rstrip("/")
CASES = json.loads((Path(__file__).resolve().parents[1] / "evals" / "prompts.json").read_text(encoding="utf-8"))


def recommend(payload: dict) -> dict:
    request = urllib.request.Request(f"{BASE}/recommend", data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read())


failures = []
for case in CASES:
    result = recommend(case["request"])
    outfits = result.get("outfits", [])
    text = " ".join(str(outfit).lower() for outfit in outfits)
    if not outfits:
        failures.append(f"{case['name']}: returned no outfits")
        continue
    if case.get("must_include") and not any(term in text for term in case["must_include"]):
        failures.append(f"{case['name']}: no expected intent evidence")
    if case.get("must_exclude") and any(term in text for term in case["must_exclude"]):
        failures.append(f"{case['name']}: excluded term appeared in results")
    if case.get("required_color") and not any(case["required_color"] in str(item).lower() for outfit in outfits for item in outfit.get("items", [])):
        failures.append(f"{case['name']}: required color was not present in item metadata")
    budget = case["request"].get("budget")
    if budget and "budget" not in result.get("meta", {}).get("relaxed_constraints", []) and any(float(outfit.get("total_price_inr", budget + 1)) > budget for outfit in outfits):
        failures.append(f"{case['name']}: returned outfit exceeded budget")
    print(f"{case['name']}: {len(outfits)} results, top={outfits[0].get('title')}")

if failures:
    raise SystemExit("\n".join(failures))
print(f"evaluation passed: {len(CASES)} cases")
