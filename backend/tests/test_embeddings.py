"""Shared local model contract for Brain and conversation recall."""
from types import ModuleType, SimpleNamespace
import sys

from app.embeddings import LocalEmbedder, embedding_service


def test_brain_and_episodes_share_embedding_instance(tmp_path):
    from app.brain.service import BrainService
    from app.memory.episodic_store import EpisodicStore

    brain = BrainService(tmp_path / "vault", tmp_path / "state.db")
    episodes = EpisodicStore(tmp_path / "state.db")
    assert brain.embedder is episodes._embed is embedding_service


def test_model_loads_once_from_local_files(monkeypatch):
    loads = []
    calls = []
    module = ModuleType("sentence_transformers")

    class Model:
        def __init__(self, name, **kwargs):
            loads.append((name, kwargs))

        def get_embedding_dimension(self):
            return 3

        def encode(self, texts, **kwargs):
            calls.append(kwargs)
            return [SimpleNamespace(tolist=lambda: [1.0, 0.0, 0.0]) for _ in texts]

    module.SentenceTransformer = Model
    monkeypatch.setitem(sys.modules, "sentence_transformers", module)
    embedder = LocalEmbedder("test-model", 3)
    assert embedder.embed_text("past conversation") == [1.0, 0.0, 0.0]
    assert len(embedder.encode(["note one", "note two"])) == 2
    assert loads == [("test-model", {"local_files_only": True})]
    assert all(call["normalize_embeddings"] for call in calls)
