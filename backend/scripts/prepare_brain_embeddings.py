"""Check the offline Brain embedding model; download only when explicitly asked."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.brain.embeddings import BrainEmbedder, BrainEmbeddingUnavailable  # noqa: E402
from app.config import settings  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare the local Brain embedding model")
    parser.add_argument("--download", action="store_true", help="Fetch model files from Hugging Face once")
    args = parser.parse_args()
    if args.download:
        from sentence_transformers import SentenceTransformer
        SentenceTransformer(settings.poseidon_embedding_model, local_files_only=False)
    try:
        embedder = BrainEmbedder()
        vector = embedder.encode(["Local Brain embedding check"])[0]
    except BrainEmbeddingUnavailable as exc:
        parser.exit(2, f"{exc}\n")
    print(f"Ready offline: {embedder.model_name} ({len(vector)} dimensions)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
