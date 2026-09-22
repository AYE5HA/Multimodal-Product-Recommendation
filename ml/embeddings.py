"""FashionCLIP catalog index and hybrid semantic scoring."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np


class FashionClipIndex:
    def __init__(self, artifact_dir: Path, model_name: str = "Marqo/marqo-fashionCLIP"):
        self.artifact_dir = artifact_dir
        self.model_name = model_name
        self.ids: list[str] = []
        self.text_vectors: np.ndarray | None = None
        self.image_vectors: np.ndarray | None = None
        self._model = None
        self._processor = None

    @property
    def available(self) -> bool:
        return bool(self.ids) and self.text_vectors is not None

    def load(self) -> "FashionClipIndex":
        ids_path = self.artifact_dir / "fashionclip_ids.json"
        text_path = self.artifact_dir / "fashionclip_text.npy"
        image_path = self.artifact_dir / "fashionclip_image.npy"
        if ids_path.exists() and text_path.exists():
            self.ids = json.loads(ids_path.read_text(encoding="utf-8"))
            self.text_vectors = np.load(text_path, mmap_mode="r")
            self.image_vectors = np.load(image_path, mmap_mode="r") if image_path.exists() else None
        return self

    def _load_model(self) -> None:
        if self._model is not None:
            return
        import torch
        from transformers import AutoModel, AutoProcessor

        self._processor = AutoProcessor.from_pretrained(self.model_name, trust_remote_code=True)
        self._model = AutoModel.from_pretrained(self.model_name, trust_remote_code=True).eval()
        self._device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self._model.to(self._device)

    def encode_text(self, text: str) -> np.ndarray:
        import torch

        self._load_model()
        encoded = self._processor(text=[text], padding="max_length", truncation=True, return_tensors="pt")
        encoded = {key: value.to(self._device) for key, value in encoded.items() if hasattr(value, "to")}
        with torch.no_grad():
            vector = self._model.get_text_features(**encoded, normalize=True)
        return vector.detach().cpu().numpy()[0]

    def text_scores(self, query: str, product_ids: list[str]) -> dict[str, float]:
        if not self.available:
            return {}
        query_vector = self.encode_text(query)
        positions = {product_id: index for index, product_id in enumerate(self.ids)}
        scores = {}
        for product_id in product_ids:
            index = positions.get(product_id)
            if index is not None:
                scores[product_id] = float(np.dot(query_vector, self.text_vectors[index]))
        return scores
