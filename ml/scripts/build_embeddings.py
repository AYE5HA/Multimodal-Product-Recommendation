"""Build FashionCLIP text/image embeddings for the local product catalog."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ml"))
from embeddings import FashionClipIndex  # noqa: E402


def main() -> None:
    data_dir = Path(os.getenv("DATA_DIR", ROOT / "data"))
    artifact_dir = Path(os.getenv("ARTIFACT_DIR", data_dir / "processed"))
    catalog = json.loads((artifact_dir / "catalog.json").read_text(encoding="utf-8"))
    index = FashionClipIndex(artifact_dir)
    index._load_model()
    import torch

    text_vectors = []
    image_vectors = []
    ids = []
    for offset in range(0, len(catalog), 16):
        batch = catalog[offset:offset + 16]
        texts = [" ".join(str(item.get(key, "")) for key in ("name", "category_label", "tags", "description", "occasion")) for item in batch]
        encoded = index._processor(text=texts, padding="max_length", truncation=True, return_tensors="pt")
        encoded = {key: value.to(index._device) for key, value in encoded.items() if hasattr(value, "to")}
        with torch.no_grad():
            text_batch = index._model.get_text_features(**encoded, normalize=True).cpu().numpy()
        image_batch = []
        for item in batch:
            try:
                with Image.open(data_dir / str(item.get("image"))) as image:
                    image_inputs = index._processor(images=image.convert("RGB"), return_tensors="pt")
                    image_inputs = {key: value.to(index._device) for key, value in image_inputs.items() if hasattr(value, "to")}
                    with torch.no_grad():
                        image_batch.append(index._model.get_image_features(**image_inputs, normalize=True).cpu().numpy()[0])
            except (OSError, ValueError):
                image_batch.append(np.zeros(text_batch.shape[1], dtype=np.float32))
        ids.extend(str(item["id"]) for item in batch)
        text_vectors.append(text_batch)
        image_vectors.extend(image_batch)
        print(f"embedded {min(offset + len(batch), len(catalog))}/{len(catalog)}")
    artifact_dir.mkdir(parents=True, exist_ok=True)
    (artifact_dir / "fashionclip_ids.json").write_text(json.dumps(ids), encoding="utf-8")
    np.save(artifact_dir / "fashionclip_text.npy", np.concatenate(text_vectors).astype(np.float32))
    np.save(artifact_dir / "fashionclip_image.npy", np.asarray(image_vectors, dtype=np.float32))
    print(f"wrote FashionCLIP index for {len(ids)} products")


if __name__ == "__main__":
    main()
