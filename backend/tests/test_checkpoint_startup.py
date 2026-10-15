"""The application keeps LangGraph checkpoints separate from owner data."""

import sqlite3

from fastapi.testclient import TestClient

from app.config import settings
from app.main import app


def test_startup_uses_separate_checkpoint_database(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, 'poseidon_checkpoint_db_path', None)
    expected = settings.poseidon_db_path.with_name('checkpoints.db')

    with TestClient(app, client=('127.0.0.1', 50000)) as client:
        assert client.get('/health').status_code == 200

    assert expected.exists()
    with sqlite3.connect(expected) as conn:
        assert conn.execute("SELECT 1 FROM sqlite_master WHERE name='checkpoints'").fetchone()
    with sqlite3.connect(settings.poseidon_db_path) as conn:
        assert not conn.execute("SELECT 1 FROM sqlite_master WHERE name='checkpoints'").fetchone()
