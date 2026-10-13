"""Probe actual runtime capabilities without touching owner data."""
import sqlite3
import sys
from tempfile import TemporaryDirectory
from pathlib import Path
from app.db.connection import connection


def check_runtime():
    if sys.version_info < (3, 11):
        raise RuntimeError('Poseidon requires Python 3.11 or newer')
    with TemporaryDirectory(prefix='poseidon-capabilities-') as tmp:
        with connection(Path(tmp) / 'probe.db', vectors=True) as conn:
            conn.execute('CREATE VIRTUAL TABLE fts_probe USING fts5(text)')
            assert conn.execute("SELECT json_extract('{\"ok\":true}', '$.ok')").fetchone()[0] == 1
            wal = conn.execute('PRAGMA journal_mode').fetchone()[0] == 'wal'
            if not wal:
                raise RuntimeError('SQLite WAL is required')
            try:
                conn.execute('SELECT vec_version()').fetchone()
                vector_mode = 'sqlite-vec'
            except sqlite3.OperationalError:
                vector_mode = 'python-cosine'
    return {'python': sys.version.split()[0], 'sqlite': sqlite3.sqlite_version, 'fts5': True, 'json': True, 'wal': wal, 'vector_mode': vector_mode}
