"""Source-backed brain ingestion and its operator-facing read endpoints."""
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.brain.service import BrainService, BrainUnavailable, Topic, TopicAssignment, classify_source
from app.brain.embeddings import BrainEmbedder, BrainEmbeddingUnavailable
from app.config import settings
from app.main import app
from app.storage.migrations import apply_migrations


class FakeEmbedder:
    model_id = "fake:3"
    dimension = 3

    def encode(self, texts):
        vectors = []
        for text in texts:
            lowered = text.casefold()
            if any(word in lowered for word in ("spinach", "vegetable", "purchase")):
                vectors.append([1.0, 0.0, 0.0])
            elif "acme" in lowered:
                vectors.append([0.0, 1.0, 0.0])
            else:
                vectors.append([0.0, 0.0, 1.0])
        return vectors


def test_brain_embedding_loader_never_substitutes_fake_vectors(monkeypatch):
    from types import ModuleType
    import sys

    module = ModuleType("sentence_transformers")

    def missing_model(*_args, **_kwargs):
        raise OSError("not cached")

    module.SentenceTransformer = missing_model
    monkeypatch.setitem(sys.modules, "sentence_transformers", module)
    with pytest.raises(BrainEmbeddingUnavailable, match="not available locally"):
        BrainEmbedder("missing-model", 3).encode(["question"])


@pytest.mark.asyncio
async def test_brain_ingest_is_source_backed_and_idempotent(tmp_path, monkeypatch):
    vault = tmp_path / "Brain"
    raw = vault / "raw"
    raw.mkdir(parents=True)
    source = raw / "meeting.md"
    source.write_text("Acme requested a weekly export. Product will review it Friday.", encoding="utf-8")
    db = tmp_path / "brain.db"
    apply_migrations(db)
    calls = []

    async def classify(text, titles):
        calls.append((text, titles))
        return TopicAssignment(nodes=[
            Topic(title="Acme", summary="Acme requested a weekly export.", evidence="Acme requested a weekly export."),
            Topic(title="Product", summary="Product will review the request Friday.", evidence="Product will review it Friday."),
        ])

    brain = BrainService(vault, db, classify, FakeEmbedder())
    brain.ensure_vault()
    original = source.read_bytes()
    first = await brain.sync("local_owner")
    assert first["processed"] == ["raw/meeting.md"]
    assert first["nodes"] == 2
    assert source.read_bytes() == original
    assert "raw/" in (vault / "schema.md").read_text(encoding="utf-8")
    nodes = brain.list_nodes("local_owner")
    acme = brain.get_node("local_owner", next(n["id"] for n in nodes if n["title"] == "Acme"))
    assert acme["sources"][0]["path"] == "raw/meeting.md"
    assert acme["links"][0]["title"] == "Product"
    graph = brain.graph("local_owner")
    assert len(graph["sources"]) == 1
    assert len(graph["topics"]) == 2
    assert len(graph["edges"]) == 2
    assert brain.graph("another_owner") == {"sources": [], "topics": [], "edges": []}
    assert (await brain.lint("local_owner"))["issues"] == []

    async def complete(**_kwargs):
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(
            content='{"answer":"Acme requested a weekly export.","citations":[1],"abstained":false}'))])

    from app.brain import service as module
    monkeypatch.setattr(module, "_brain_model", lambda: (
        SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=complete))), "test-model"))
    answer = await brain.query("local_owner", "What did Acme request?")
    assert answer["answer"] == "Acme requested a weekly export."
    assert answer["sources"][0]["path"] == "raw/meeting.md"
    assert (await brain.query("local_owner", "unrelatedxyz"))["sources"] == []
    assert "ingest" in (vault / "log.md").read_text(encoding="utf-8")
    page = (vault / "wiki" / acme["file_name"]).read_text(encoding="utf-8")
    assert "[Source](../raw/meeting.md)" in page
    assert "[[product-" in page

    second = await brain.sync("local_owner")
    assert second["unchanged"] == ["raw/meeting.md"]
    assert len(calls) == 1

    source.write_text("Acme requested a weekly export. Product will review it Friday.\n", encoding="utf-8")
    assert {issue["kind"] for issue in (await brain.lint("local_owner"))["issues"]} == {"changed_source"}
    assert (await brain.query("local_owner", "What did Acme request?"))["sources"][0]["path"] == "raw/meeting.md"
    assert len(calls) == 2
    assert len(brain.get_node("local_owner", acme["id"])["sources"]) == 1
    assert (await brain.lint("local_owner"))["issues"] == []


@pytest.mark.asyncio
async def test_brain_retrieves_raw_passage_outside_topic_summary(tmp_path, monkeypatch):
    vault = tmp_path / "Brain"
    raw = vault / "raw"
    raw.mkdir(parents=True)
    (raw / "plan.md").write_text(
        "# Weekly plan\n\nMonday is for planning.\n" + "Planning details. " * 90 +
        "Buy spinach and lentils on Wednesday.", encoding="utf-8")
    db = tmp_path / "brain.db"
    apply_migrations(db)

    async def classify(_text, _titles):
        return TopicAssignment(nodes=[Topic(
            title="Planning", summary="Monday is for planning.", evidence="Monday is for planning.")])

    brain = BrainService(vault, db, classify, FakeEmbedder())
    await brain.sync("local_owner")
    from app.storage.connection import connection
    with connection(db) as conn:
        assert conn.execute("SELECT COUNT(*) FROM brain_chunks").fetchone()[0] > 1
    prompts = []

    async def complete(**kwargs):
        prompts.append(kwargs["messages"][1]["content"])
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(
            content='{"answer":"Buy spinach and lentils on Wednesday.","citations":[1],"abstained":false}'))])

    from app.brain import service as module
    monkeypatch.setattr(module, "_brain_model", lambda: (
        SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=complete))), "test-model"))
    result = await brain.query("local_owner", "When should I buy spinach?")
    assert "Buy spinach and lentils" in prompts[0]
    assert result["sources"][0]["path"] == "raw/plan.md"
    assert result["sources"][0]["title"] == "Weekly plan"
    paraphrase = await brain.query("local_owner", "Which vegetables should I purchase?")
    assert paraphrase["sources"][0]["path"] == "raw/plan.md"


@pytest.mark.asyncio
async def test_brain_removes_deleted_source_and_backfills_existing_chunks(tmp_path):
    vault = tmp_path / "Brain"
    raw = vault / "raw"
    raw.mkdir(parents=True)
    source = raw / "plan.md"
    source.write_text("Buy spinach on Wednesday.", encoding="utf-8")
    db = tmp_path / "brain.db"
    apply_migrations(db)

    async def classify(_text, _titles):
        return TopicAssignment(nodes=[Topic(title="Groceries", summary="Buy spinach on Wednesday.",
                                            evidence="Buy spinach on Wednesday.")])

    brain = BrainService(vault, db, classify, FakeEmbedder())
    await brain.sync("local_owner")
    from app.storage.connection import connection
    with connection(db) as conn:
        conn.execute("DELETE FROM brain_chunks")
        conn.commit()
    assert (await brain.sync("local_owner"))["unchanged"] == ["raw/plan.md"]
    with connection(db) as conn:
        assert conn.execute("SELECT COUNT(*) FROM brain_chunks").fetchone()[0] == 1

    source.unlink()
    assert (await brain.query("local_owner", "spinach"))["sources"] == []
    assert brain.graph("local_owner") == {"sources": [], "topics": [], "edges": []}
    assert brain.list_nodes("local_owner") == []


@pytest.mark.asyncio
async def test_brain_reembeds_when_configured_model_changes(tmp_path):
    vault = tmp_path / "Brain"
    raw = vault / "raw"
    raw.mkdir(parents=True)
    (raw / "plan.md").write_text("Buy spinach on Wednesday.", encoding="utf-8")
    db = tmp_path / "brain.db"
    apply_migrations(db)
    classifications = []

    async def classify(_text, _titles):
        classifications.append(1)
        return TopicAssignment(nodes=[Topic(title="Groceries", summary="Buy spinach on Wednesday.",
                                            evidence="Buy spinach on Wednesday.")])

    first = BrainService(vault, db, classify, FakeEmbedder())
    await first.sync("local_owner")

    class NewModel(FakeEmbedder):
        model_id = "new-model:3"

    second = BrainService(vault, db, classify, NewModel())
    assert (await second.sync("local_owner"))["unchanged"] == ["raw/plan.md"]
    assert len(classifications) == 1
    from app.storage.connection import connection
    with connection(db) as conn:
        assert conn.execute("SELECT DISTINCT model_id FROM brain_chunk_embeddings").fetchone()[0] == "new-model:3"


@pytest.mark.asyncio
async def test_brain_rejects_unsupported_evidence_without_writing(tmp_path):
    vault = tmp_path / "Brain"
    (vault / "raw").mkdir(parents=True)
    (vault / "raw" / "note.txt").write_text("The launch is on Friday.", encoding="utf-8")
    db = tmp_path / "brain.db"
    apply_migrations(db)

    async def classify(_text, _titles):
        return TopicAssignment(nodes=[Topic(title="Launch", summary="The launch is Friday.", evidence="The launch is Monday.")])

    brain = BrainService(vault, db, classify, FakeEmbedder())
    result = await brain.sync("local_owner")
    assert result["processed"] == []
    assert "absent from the source" in result["failed"][0]["error"]
    assert brain.list_nodes("local_owner") == []


@pytest.mark.asyncio
async def test_pasted_source_is_saved_and_filed(tmp_path):
    vault = tmp_path / "Brain"
    db = tmp_path / "brain.db"
    apply_migrations(db)

    async def classify(_text, _titles):
        return TopicAssignment(nodes=[Topic(
            title="Roadmap", summary="The roadmap prioritizes retrieval.",
            evidence="The roadmap prioritizes retrieval.")])

    brain = BrainService(vault, db, classify, FakeEmbedder())
    result = await brain.add_source("local_owner", "Team update", "The roadmap prioritizes retrieval.", source_key="telegram:123")
    assert result["path"].startswith("raw/team-update-")
    assert result["scan"]["processed"] == [result["path"]]
    assert "The roadmap prioritizes retrieval." in (vault / result["path"]).read_text(encoding="utf-8")
    assert brain.list_nodes("local_owner")[0]["title"] == "Roadmap"
    repeated = await brain.add_source("local_owner", "Team update", "The roadmap prioritizes retrieval.", source_key="telegram:123")
    assert repeated["path"] == result["path"]
    assert repeated["scan"]["unchanged"] == [result["path"]]


@pytest.mark.asyncio
async def test_brain_blocks_remote_inference_by_default(monkeypatch):
    from app.brain import service as module

    monkeypatch.setattr(settings, "poseidon_brain_allow_remote_model", False)
    monkeypatch.setattr(module.llm_provider, "get_agent_resolved_config", lambda _: {"base_url": "https://example.com/v1", "model": "test"})
    with pytest.raises(BrainUnavailable, match="local model"):
        await classify_source("A note", [])


def test_brain_read_api(tmp_path, monkeypatch):
    vault = tmp_path / "Brain"
    vault.mkdir()
    db = tmp_path / "brain.db"
    apply_migrations(db)
    monkeypatch.setattr(settings, "poseidon_brain_vault_path", vault)
    monkeypatch.setattr(settings, "poseidon_db_path", db)
    client = TestClient(app, client=("127.0.0.1", 50000))
    assert client.get("/brain/status").json()["vault_exists"] is True
    assert client.get("/brain/nodes").json() == []
    assert client.get("/brain/graph").json() == {"sources": [], "topics": [], "edges": []}
    assert client.post("/brain/query", json={"question": "Where is the plan?"}).json()["sources"] == []
    assert client.post("/brain/lint").json()["issues"] == []
    assert client.get("/brain/nodes/missing").status_code == 404


def test_default_vault_follows_isolated_database(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "poseidon_db_path", tmp_path / "state.db")
    monkeypatch.setattr(settings, "poseidon_brain_vault_path", None)
    assert settings.brain_vault_path == tmp_path / "brain"
    brain = BrainService(settings.brain_vault_path, settings.poseidon_db_path)
    brain.ensure_vault()
    assert (tmp_path / "brain" / "raw").is_dir()
    assert (tmp_path / "brain" / "wiki").is_dir()
