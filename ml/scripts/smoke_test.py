"""Run a dependency-free smoke test against a running ML service."""
import json
import os
import urllib.request


BASE = os.getenv("ML_SERVICE_URL", "http://127.0.0.1:8000").rstrip("/")


def request(url: str, payload: dict | None = None) -> dict:
    body = None if payload is None else json.dumps(payload).encode()
    request_obj = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"} if body else {})
    with urllib.request.urlopen(request_obj, timeout=10) as response:
        return json.loads(response.read())


health = request(f"{BASE}/health")
assert health["status"] == "ok", health
assert health["products"] > 0 and health["outfits"] > 0, health
result = request(f"{BASE}/recommend", {"query": "women party evening look", "gender": "women", "occasion": "party", "k": 2})
assert len(result["outfits"]) > 0, result
assert all(item["items"] and item["evidence"] for item in result["outfits"]), result
print(f"smoke ok: {len(result['outfits'])} grounded outfits from {health['products']} products")
