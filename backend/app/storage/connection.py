from contextlib import contextmanager
from pathlib import Path
import logging
import sqlite3

logger = logging.getLogger(__name__)


@contextmanager
def connection(db_path, *, vectors=False):
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), timeout=5.0)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute('PRAGMA journal_mode=WAL')
        conn.execute('PRAGMA foreign_keys=ON')
        conn.execute('PRAGMA busy_timeout=5000')
        if vectors:
            extension_enabled = False
            try:
                import sqlite_vec
                conn.enable_load_extension(True)
                extension_enabled = True
                sqlite_vec.load(conn)
            except (ImportError, OSError, AttributeError, sqlite3.Error) as exc:
                logger.info('sqlite-vec unavailable; using Python cosine retrieval: %s', type(exc).__name__)
            finally:
                if extension_enabled:
                    conn.enable_load_extension(False)
        yield conn
    finally:
        conn.close()
