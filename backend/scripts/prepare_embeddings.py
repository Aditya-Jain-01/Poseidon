"""Check the offline shared embedding model; download only when explicitly asked."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.embeddings import LocalEmbedder, EmbeddingUnavailable  # noqa: E402
from app.config import settings  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare the local shared embedding model")
    parser.add_argument("--download", action="store_true", help="Fetch model files from Hugging Face once")
    args = parser.parse_args()
    if args.download:
        from sentence_transformers import SentenceTransformer
        SentenceTransformer(settings.poseidon_embedding_model, local_files_only=False)
    try:
        embedder = LocalEmbedder()
        vector = embedder.encode(["Local shared embedding check"])[0]
    except EmbeddingUnavailable as exc:
        parser.exit(2, f"{exc}\n")
    print(f"Ready offline: {embedder.model_name} ({len(vector)} dimensions)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
