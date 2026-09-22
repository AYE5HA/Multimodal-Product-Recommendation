"""Validate source CSVs and fail early on broken catalog relationships."""
from pathlib import Path
import csv

ROOT = Path(__file__).resolve().parents[2]
def read(name: str, required: set[str]) -> list[dict[str, str]]:
    with (ROOT / "data" / name).open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        headers = set(reader.fieldnames or [])
        rows = list(reader)
    missing = required - headers
    if missing:
        raise SystemExit(f"{name} missing columns: {', '.join(sorted(missing))}")
    if not rows:
        raise SystemExit(f"{name} is empty")
    print(f"{name}: {len(rows)} rows, valid")
    return rows


products = read("products.csv", {"id", "name", "price_inr", "image"})
outfits = read("outfits.csv", {"outfit_id", "hero_id"})
product_ids = {row["id"] for row in products}
missing_ids = sorted({row[key] for row in outfits for key in ("hero_id", "second_id", "layer_id", "footwear_id", "accessory_1_id", "accessory_2_id") if row.get(key) and row[key] not in product_ids})
if missing_ids:
    raise SystemExit(f"outfits.csv references {len(missing_ids)} missing product ids: {', '.join(missing_ids[:5])}")
