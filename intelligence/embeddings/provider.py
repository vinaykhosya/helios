"""
intelligence/embeddings/provider.py

LocalEmbeddingProvider — zero-cost semantic embeddings using sentence-transformers.
Model: all-MiniLM-L6-v2 (384 dimensions, normalized float32 vectors).
"""
from __future__ import annotations

import asyncio
from typing import Optional


class LocalEmbeddingProvider:
    model_name = "sentence-transformers/all-MiniLM-L6-v2"
    dimensions = 384

    def __init__(self, model_name: Optional[str] = None):
        if model_name:
            self.model_name = model_name
        self._model = None

    def _load(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.model_name)

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """
        Embed a list of texts. Returns list of 384-d float vectors.
        Runs in thread executor to avoid blocking the async event loop.
        """
        if not texts:
            return []
        self._load()
        loop = asyncio.get_running_loop()
        vectors = await loop.run_in_executor(
            None,
            lambda: self._model.encode(texts, normalize_embeddings=True).tolist()
        )
        return vectors
