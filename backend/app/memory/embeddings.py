"""Local Embedding Service — generates 384-dim vectors using sentence-transformers.

Uses the all-MiniLM-L6-v2 model (22M params, ~90MB) for fast, offline,
privacy-preserving text embeddings.  The model is loaded lazily on first use
so that import-time stays fast during tests or when embeddings aren't needed.
"""

import logging
from typing import TYPE_CHECKING

from app.config import settings

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


class LocalEmbeddingService:
    """Singleton wrapper around sentence-transformers for local embeddings."""

    def __init__(self, model_name: str | None = None) -> None:
        self._model_name = model_name or settings.poseidon_embedding_model
        self._model: "SentenceTransformer | None" = None

    def _load_model(self) -> "SentenceTransformer":
        """Lazy-load the model on first call."""
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            logger.info("Loading embedding model '%s' …", self._model_name)
            self._model = SentenceTransformer(self._model_name)
            logger.info("Embedding model loaded (dim=%d).", self._model.get_sentence_embedding_dimension())
        return self._model

    def embed_text(self, text: str) -> list[float]:
        """Convert a single text string into a 384-dim float vector."""
        model = self._load_model()
        # encode() returns an ndarray; convert to plain list[float]
        vector = model.encode(text, normalize_embeddings=True)
        return vector.tolist()

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Convert a batch of texts into vectors (more efficient than one-by-one)."""
        model = self._load_model()
        vectors = model.encode(texts, normalize_embeddings=True, batch_size=32)
        return vectors.tolist()

    @property
    def dim(self) -> int:
        """Return the configured embedding dimension."""
        return settings.poseidon_embedding_dim


# App-wide singleton — lazy; model loads on first .embed_text() call
embedding_service = LocalEmbeddingService()
