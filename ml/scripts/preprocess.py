"""Build local, reproducible catalogue artifacts without model downloads."""
from __future__ import annotations
import csv, json, math, re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
OUT = DATA / "processed"

def tokens(value: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", (value or "").lower())

def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    with (DATA / "products.csv").open(encoding="utf-8", newline="") as handle:
        products = list(csv.DictReader(handle))
    catalog = []
    for product in products:
        product["text"] = " ".join(tokens(" ".join(product.get(key, "") for key in ("name", "category_label", "tags", "description"))))
        catalog.append(product)
    (OUT / "catalog.json").write_text(json.dumps(catalog, indent=2), encoding="utf-8")
    vocab = sorted({token for item in catalog for token in item["text"].split()})
    (OUT / "vocabulary.json").write_text(json.dumps(vocab), encoding="utf-8")
    print(f"Wrote {len(catalog)} products and {len(vocab)} vocabulary terms to {OUT}")

if __name__ == "__main__":
    main()
