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

    def _load_model(self) -> "SentenceTransformer | None":
        """Lazy-load the model on first call if available."""
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                logger.info("Loading embedding model '%s' …", self._model_name)
                self._model = SentenceTransformer(self._model_name)
                logger.info("Embedding model loaded (dim=%d).", self._model.get_sentence_embedding_dimension())
            except ImportError:
                logger.warning("sentence_transformers not installed; falling back to deterministic embedding.")
                self._model = False  # Sentinel indicating unavailable
        return self._model if self._model is not False else None

    def _fallback_embed(self, text: str) -> list[float]:
        """Generate a fast deterministic 384-dim pseudo-vector when model is unavailable."""
        import random
        rng = random.Random(text)
        vec = [rng.gauss(0, 1) for _ in range(self.dim)]
        norm = sum(v * v for v in vec) ** 0.5 or 1.0
        return [v / norm for v in vec]

    def embed_text(self, text: str) -> list[float]:
        """Convert a single text string into a 384-dim float vector."""
        model = self._load_model()
        if model is None:
            return self._fallback_embed(text)
        vector = model.encode(text, normalize_embeddings=True)
        return vector.tolist()

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Convert a batch of texts into vectors (more efficient than one-by-one)."""
        model = self._load_model()
        if model is None:
            return [self._fallback_embed(t) for t in texts]
        vectors = model.encode(texts, normalize_embeddings=True, batch_size=32)
        return vectors.tolist()

    @property
    def dim(self) -> int:
        """Return the configured embedding dimension."""
        return settings.poseidon_embedding_dim


# App-wide singleton — lazy; model loads on first .embed_text() call
embedding_service = LocalEmbeddingService()
