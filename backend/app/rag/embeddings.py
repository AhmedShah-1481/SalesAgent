"""Local embeddings — sentence-transformers all-MiniLM-L6-v2 (free, no API cost).

Implemented as a thin LangChain ``Embeddings`` wrapper around sentence-transformers so
we depend only on requirements-ml.txt (no langchain-huggingface) and load the model once,
lazily. Vectors are L2-normalized so the Chroma "cosine" space yields clean 0-1 scores.
"""
from __future__ import annotations

from functools import lru_cache

from langchain_core.embeddings import Embeddings

from app.config import get_settings


class LocalEmbeddings(Embeddings):
    """Wraps a sentence-transformers model. The model is loaded on first use only."""

    def __init__(self, model_name: str) -> None:
        self._model_name = model_name
        self._model = None  # heavy; loaded lazily so importing this module is cheap

    @property
    def model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer  # lazy: pulls torch

            self._model = SentenceTransformer(self._model_name)
        return self._model

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        vectors = self.model.encode(
            list(texts), normalize_embeddings=True, convert_to_numpy=True
        )
        return vectors.tolist()

    def embed_query(self, text: str) -> list[float]:
        vector = self.model.encode(
            [text], normalize_embeddings=True, convert_to_numpy=True
        )[0]
        return vector.tolist()


@lru_cache
def get_embeddings() -> Embeddings:
    """Process-wide singleton so the model weights load exactly once."""
    return LocalEmbeddings(get_settings().embedding_model)
