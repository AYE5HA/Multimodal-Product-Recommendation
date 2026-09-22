"""Validate the source CSVs before preprocessing."""
from pathlib import Path
import csv

ROOT = Path(__file__).resolve().parents[2]
for name, required in (("products.csv", {"id", "name", "price_inr", "image"}), ("outfits.csv", {"outfit_id", "hero_id"})):
    with (ROOT / "data" / name).open(encoding="utf-8", newline="") as handle:
        headers = set(next(csv.reader(handle)))
    missing = required - headers
    if missing:
        raise SystemExit(f"{name} missing columns: {', '.join(sorted(missing))}")
    print(f"{name}: valid")
