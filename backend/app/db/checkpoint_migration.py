"""Move legacy LangGraph checkpoints out of the application data database."""

from pathlib import Path

from app.db.connection import connection


def copy_legacy_checkpoints(data_db_path: Path, checkpoint_db_path: Path) -> bool:
    """Copy existing checkpoints once, before the new saver handles any runs."""
    source = Path(data_db_path).resolve()
    target = Path(checkpoint_db_path).resolve()
    if source == target or not source.exists():
        return False

    with connection(target) as conn:
        if conn.execute('SELECT 1 FROM checkpoints LIMIT 1').fetchone():
            return False
        conn.execute('ATTACH DATABASE ? AS legacy', (str(source),))
        try:
            if not conn.execute("SELECT 1 FROM legacy.sqlite_master WHERE type='table' AND name='checkpoints'").fetchone():
                return False
            columns = {row['name'] for row in conn.execute('PRAGMA legacy.table_info(writes)')}
            task_path = 'task_path' if 'task_path' in columns else "''"
            with conn:
                conn.execute('''INSERT INTO checkpoints(thread_id,checkpoint_ns,checkpoint_id,parent_checkpoint_id,type,checkpoint,metadata)
                                SELECT thread_id,checkpoint_ns,checkpoint_id,parent_checkpoint_id,type,checkpoint,metadata
                                FROM legacy.checkpoints''')
                if columns:
                    conn.execute(f'''INSERT INTO writes(thread_id,checkpoint_ns,checkpoint_id,task_id,task_path,idx,channel,type,value)
                                     SELECT thread_id,checkpoint_ns,checkpoint_id,task_id,{task_path},idx,channel,type,value
                                     FROM legacy.writes''')
            return True
        finally:
            conn.execute('DETACH DATABASE legacy')
