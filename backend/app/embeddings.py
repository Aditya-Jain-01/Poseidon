"""Strict, offline sentence embeddings for Brain and episodic retrieval."""
from __future__ import annotations

from app.config import settings


class EmbeddingUnavailable(RuntimeError):
    """The configured local embedding model cannot be used."""


class LocalEmbedder:
    def __init__(self, model_name: str | None = None, dimension: int | None = None):
        self.model_name = model_name or settings.poseidon_embedding_model
        self.dimension = dimension or settings.poseidon_embedding_dim
        self.model_id = f"{self.model_name}:{self.dimension}"
        self._model = None

    def embed_text(self, text: str) -> list[float]:
        return self.encode([text])[0]

    def encode(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._model = SentenceTransformer(self.model_name, local_files_only=True)
            except Exception as exc:
                raise EmbeddingUnavailable(
                    f"Embedding model '{self.model_name}' is not available locally. "
                    "Run python backend/scripts/prepare_embeddings.py --download once during setup."
                ) from exc
            actual_dim = self._model.get_embedding_dimension()
            if actual_dim != self.dimension:
                self._model = None
                raise EmbeddingUnavailable(
                    f"Embedding model has {actual_dim} dimensions; POSEIDON_EMBEDDING_DIM is {self.dimension}"
                )
        try:
            vectors = self._model.encode(texts, normalize_embeddings=True, show_progress_bar=False, batch_size=32)
            return [vector.tolist() for vector in vectors]
        except Exception as exc:
            raise EmbeddingUnavailable("Embedding inference failed") from exc


embedding_service = LocalEmbedder()
