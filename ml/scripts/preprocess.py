"""Build local, reproducible catalogue artifacts without model downloads."""
from __future__ import annotations
import csv, json, re
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
        try:
            product["price_inr"] = round(float(product.get("price_inr") or 0), 2)
        except ValueError:
            product["price_inr"] = 0.0
        product["id"] = product.get("id", "").strip()
        # Do not preserve stale remote URLs from older catalog exports; the
        # running app serves the checked-in image asset from /data.
        product["image_url"] = ""
        product["text"] = " ".join(tokens(" ".join(product.get(key, "") for key in ("name", "category_label", "tags", "description"))))
        catalog.append(product)
    (OUT / "catalog.json").write_text(json.dumps(catalog, indent=2), encoding="utf-8")
    vocab = sorted({token for item in catalog for token in item["text"].split()})
    (OUT / "vocabulary.json").write_text(json.dumps(vocab), encoding="utf-8")
    report = {
        "products": len(catalog),
        "unique_ids": len({item["id"] for item in catalog}),
        "missing_images": sum(not item.get("image") for item in catalog),
        "zero_prices": sum(item["price_inr"] <= 0 for item in catalog),
        "vocabulary_terms": len(vocab),
    }
    (OUT / "quality_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Wrote {len(catalog)} products, {len(vocab)} vocabulary terms, quality report to {OUT}")

if __name__ == "__main__":
    main()
