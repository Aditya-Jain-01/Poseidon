"""Transactional, owner-scoped repositories for Poseidon's personal tools."""
from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
from typing import Any

from app.config import settings
from app.db.connection import connection
from app.db.migrations import apply_migrations


class PersonalDataRepository:
    def __init__(self, db_path: Path | str | None = None):
        self.db_path = Path(db_path or settings.poseidon_db_path)

    def _prepare(self):
        apply_migrations(self.db_path, settings.poseidon_embedding_dim)
        self._import_legacy_once()

    def _import_legacy_once(self):
        root = self.db_path.parent
        sources = {'notes.json': 'notes', 'calendar.json': 'calendar', 'crm_data.json': 'crm'}
        for filename, kind in sources.items():
            source = root / filename
            if not source.exists():
                continue
            raw = source.read_bytes()
            checksum = hashlib.sha256(raw).hexdigest()
            with connection(self.db_path) as conn:
                existing = conn.execute('SELECT checksum FROM personal_imports WHERE source_name=?', (filename,)).fetchone()
                if existing:
                    continue
                backup = source.with_name(f'{source.name}.poseidon-backup-{datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")}')
                shutil.copy2(source, backup)
                data = json.loads(raw)
                conn.execute('BEGIN IMMEDIATE')
                try:
                    if kind == 'notes':
                        for bucket, row_kind in (('notes', 'note'), ('reminders', 'reminder')):
                            for row in data.get(bucket, []):
                                conn.execute('INSERT OR IGNORE INTO notes(id,owner_id,kind,text,due_at) VALUES (?,?,?,?,?)', (row.get('id') or str(uuid4()), 'local_owner', row_kind, row.get('text', ''), row.get('due_at')))
                    elif kind == 'calendar':
                        for row in data.get('events', []):
                            conn.execute('INSERT OR IGNORE INTO calendar_events(id,owner_id,title,starts_at_utc,ends_at_utc,original_timezone,description) VALUES (?,?,?,?,?,?,?)', (row.get('id') or str(uuid4()), 'local_owner', row.get('title', ''), row.get('starts_at', ''), row.get('ends_at'), 'UTC', row.get('description', '')))
                    else:
                        for row in data.get('contacts', []):
                            ident = row.get('id') or str(uuid4())
                            row = {**row, 'id': ident}
                            conn.execute('INSERT OR IGNORE INTO crm_contacts(id,owner_id,payload_json) VALUES (?,?,?)', (ident, 'local_owner', json.dumps(row)))
                    conn.execute('INSERT INTO personal_imports(source_name,checksum) VALUES (?,?)', (filename, checksum))
                    conn.commit()
                except BaseException:
                    conn.rollback()
                    raise

    def notes_read(self, owner_id: str, query: str = ''):
        self._prepare(); query = query.lower().strip()
        with connection(self.db_path) as conn:
            rows = [dict(r) for r in conn.execute('SELECT id,kind,text,due_at FROM notes WHERE owner_id=? ORDER BY created_at DESC', (owner_id,))]
        grouped = {'notes': [], 'reminders': []}
        for row in rows:
            if query and query not in str(row).lower(): continue
            row.pop('kind'); grouped['notes' if row['due_at'] is None else 'reminders'].append({k:v for k,v in row.items() if v is not None})
        return grouped

    def note_create(self, owner_id, kind, text, due_at=None, source_message_id=None):
        self._prepare(); ident = str(uuid4())
        with connection(self.db_path) as conn:
            conn.execute('INSERT INTO notes(id,owner_id,kind,text,due_at,source_message_id) VALUES (?,?,?,?,?,?)', (ident, owner_id, kind, text, due_at, source_message_id)); conn.commit()
        item = {'id': ident, 'text': text};
        if due_at: item['due_at'] = due_at
        return {'created': item, 'kind': kind}

    def note_delete(self, owner_id, kind, item_id):
        self._prepare()
        with connection(self.db_path) as conn:
            cur = conn.execute('DELETE FROM notes WHERE id=? AND owner_id=? AND kind=?', (item_id, owner_id, kind)); conn.commit()
        if not cur.rowcount: raise ValueError(f'{kind} not found')
        return {'deleted': item_id, 'kind': kind}

    def calendar_read(self, owner_id, query=''):
        self._prepare(); query = query.lower().strip()
        with connection(self.db_path) as conn: rows = [dict(r) for r in conn.execute('SELECT id,title,starts_at_utc,ends_at_utc,original_timezone,description FROM calendar_events WHERE owner_id=? ORDER BY starts_at_utc', (owner_id,))]
        events = [{'id':r['id'],'title':r['title'],'starts_at':r['starts_at_utc'],'ends_at':r['ends_at_utc'],'timezone':r['original_timezone'],'description':r['description']} for r in rows if not query or query in str(r).lower()]
        return {'events': events, 'count': len(events)}

    def calendar_create(self, owner_id, title, starts_at, ends_at=None, description='', timezone_name='UTC'):
        self._prepare(); ident = str(uuid4())
        with connection(self.db_path) as conn:
            conn.execute('INSERT INTO calendar_events(id,owner_id,title,starts_at_utc,ends_at_utc,original_timezone,description) VALUES (?,?,?,?,?,?,?)', (ident,owner_id,title,starts_at,ends_at,timezone_name,description)); conn.commit()
        return {'created': {'id':ident,'title':title,'starts_at':starts_at,'ends_at':ends_at,'timezone':timezone_name,'description':description}}

    def crm_read(self, owner_id, query=''):
        self._prepare(); query=query.lower().strip()
        with connection(self.db_path) as conn: rows = [json.loads(r['payload_json']) for r in conn.execute('SELECT payload_json FROM crm_contacts WHERE owner_id=?', (owner_id,))]
        rows = [row for row in rows if not query or query in str(row).lower()]
        return {'contacts': rows, 'count': len(rows)}

    def crm_write(self, owner_id, action, contact=None, contact_id=None):
        self._prepare(); action=action.lower()
        with connection(self.db_path) as conn:
            if action == 'create':
                row = dict(contact or {}); row.setdefault('id', str(uuid4())); conn.execute('INSERT INTO crm_contacts(id,owner_id,payload_json) VALUES (?,?,?)',(row['id'],owner_id,json.dumps(row))); result={'created':row}
            else:
                found=conn.execute('SELECT payload_json FROM crm_contacts WHERE id=? AND owner_id=?',(contact_id,owner_id)).fetchone()
                if not found: raise ValueError('Contact not found')
                if action == 'delete': conn.execute('DELETE FROM crm_contacts WHERE id=? AND owner_id=?',(contact_id,owner_id)); result={'deleted':contact_id}
                elif action == 'update':
                    row=json.loads(found['payload_json']); row.update(contact or {}); conn.execute('UPDATE crm_contacts SET payload_json=?,updated_at=CURRENT_TIMESTAMP WHERE id=? AND owner_id=?',(json.dumps(row),contact_id,owner_id)); result={'updated':row}
                else: raise ValueError('crm_write action must be create, update, or delete')
            conn.commit(); return result


personal_data = PersonalDataRepository()
