"""Durable, argument-bound approval and execution repositories."""
from __future__ import annotations
import hashlib
import json
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from app.config import settings
from app.db.connection import connection
from app.db.migrations import apply_migrations
from app.models import ConversationKey
from app.security.guardrails import GuardrailRateLimitError, HarnessPausedError, record_limit_alert


def canonical_json(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)


def argument_hash(arguments):
    return hashlib.sha256(canonical_json(arguments).encode()).hexdigest()


def now():
    return datetime.now(timezone.utc)


class ApprovalStore:
    def __init__(self, db_path=None):
        self._db_path = db_path

    @property
    def db_path(self):
        return self._db_path or settings.poseidon_db_path

    def park(self, run_id, tool_call, context):
        apply_migrations(self.db_path)
        key = ConversationKey.model_validate(context['conversation_key'])
        timestamp = now()
        policy_version = context.get('policy_decision', {}).get('policy_version') or '1'
        values = (str(uuid4()), run_id, key.owner_id, canonical_json(key.model_dump()), tool_call['id'],
                  tool_call['name'], canonical_json(tool_call.get('arguments', {})), argument_hash(tool_call.get('arguments', {})),
                  policy_version, timestamp.isoformat(), (timestamp + timedelta(seconds=settings.poseidon_approval_timeout_seconds)).isoformat())
        with connection(self.db_path) as conn:
            conn.execute('BEGIN IMMEDIATE')
            try:
                row = conn.execute('SELECT * FROM approvals WHERE run_id=? AND tool_call_id=?', (run_id, tool_call['id'])).fetchone()
                if row is None:
                    if conn.execute('SELECT paused FROM guardrail_state WHERE id=1').fetchone()[0]:
                        raise HarnessPausedError('Tool execution is paused by the operator')
                    cutoff = (timestamp - timedelta(hours=1)).isoformat()
                    count = conn.execute('SELECT COUNT(*) FROM approvals WHERE created_at>=?', (cutoff,)).fetchone()[0]
                    if count >= settings.poseidon_max_approval_requests_per_hour:
                        record_limit_alert(conn, 'approval', timestamp)
                        conn.commit()
                        raise GuardrailRateLimitError('Approval request limit reached for this hour')
                    conn.execute("INSERT INTO approvals(approval_id,run_id,owner_id,conversation_key_json,tool_call_id,tool_name,canonical_arguments_json,arguments_hash,policy_version,created_at,expires_at,status) VALUES (?,?,?,?,?,?,?,?,?,?,?,'pending')", values)
                    row = conn.execute('SELECT * FROM approvals WHERE run_id=? AND tool_call_id=?', (run_id, tool_call['id'])).fetchone()
                if row['arguments_hash'] != values[7] or row['tool_name'] != tool_call['name'] or row['conversation_key_json'] != values[3]:
                    raise ValueError('Approval replay changed its execution binding')
                if row['policy_version'] != policy_version:
                    raise ValueError('Approval policy version mismatch')
                conn.commit()
            except BaseException:
                conn.rollback()
                raise
        return self.public(dict(row))

    def expire_pending(self):
        apply_migrations(self.db_path)
        with connection(self.db_path) as conn:
            with conn:
                return conn.execute("UPDATE approvals SET status='expired', resolved_at=? WHERE status IN ('pending','approved') AND expires_at<=?", (now().isoformat(), now().isoformat())).rowcount

    def get(self, approval_id):
        self.expire_pending()
        with connection(self.db_path) as conn:
            row = conn.execute('SELECT * FROM approvals WHERE approval_id=?', (approval_id,)).fetchone()
        if row is None:
            raise KeyError('Approval request not found')
        return dict(row)

    def validate(self, request, owner_id, tool_call, conversation_key, *, policy_version=None):
        if request['owner_id'] != owner_id:
            raise ValueError('Approval owner mismatch')
        if request['conversation_key_json'] != canonical_json(conversation_key):
            raise ValueError('Approval conversation mismatch')
        if request['tool_call_id'] != tool_call['id'] or request['tool_name'] != tool_call['name']:
            raise ValueError('Approval tool binding mismatch')
        if request['arguments_hash'] != argument_hash(tool_call.get('arguments', {})):
            raise ValueError('Approval arguments mismatch')
        if policy_version is not None and request['policy_version'] != policy_version:
            raise ValueError('Approval policy version mismatch')
        if request['status'] == 'expired' or request['expires_at'] <= now().isoformat():
            raise ValueError('Approval expired')

    def resolve(self, approval_id, decision, *, owner_id='local_owner'):
        if decision not in {'approved', 'denied'}:
            raise ValueError('decision must be approved or denied')
        request = self.get(approval_id)
        if request['owner_id'] != owner_id:
            raise ValueError('Approval owner mismatch')
        if request['status'] == decision or (request['status'] == 'consumed' and decision == 'approved'):
            # Retry a decision whose graph resume was interrupted before completion.
            return request
        with connection(self.db_path) as conn:
            with conn:
                changed = conn.execute("UPDATE approvals SET status=?, resolved_at=? WHERE approval_id=? AND owner_id=? AND status='pending' AND expires_at>?", (decision, now().isoformat(), approval_id, owner_id, now().isoformat())).rowcount
                if changed != 1:
                    raise ValueError('Approval expired or already resolved')
        return self.get(approval_id)

    def consume(self, approval_id, owner_id, tool_call, conversation_key, *, policy_version=None):
        request = self.get(approval_id)
        self.validate(request, owner_id, tool_call, conversation_key, policy_version=policy_version)
        with connection(self.db_path) as conn:
            with conn:
                changed = conn.execute("UPDATE approvals SET status='consumed', consumed_at=? WHERE approval_id=? AND status='approved' AND expires_at>?", (now().isoformat(), approval_id, now().isoformat())).rowcount
                if changed != 1 and request['status'] != 'consumed':
                    raise ValueError('Approval cannot be consumed')
        return request

    def invalidate(self, approval_id):
        with connection(self.db_path) as conn:
            with conn:
                conn.execute("UPDATE approvals SET status='expired', resolved_at=? WHERE approval_id=? AND status IN ('pending','approved')", (now().isoformat(), approval_id))

    def get_pending_for_user(self, user_id, conversation_key=None):
        self.expire_pending()
        sql = "SELECT * FROM approvals WHERE owner_id=? AND status='pending'"
        params = [user_id]
        if conversation_key is not None:
            sql += ' AND conversation_key_json=?'
            params.append(canonical_json(conversation_key.model_dump() if isinstance(conversation_key, ConversationKey) else conversation_key))
        with connection(self.db_path) as conn:
            row = conn.execute(sql + ' ORDER BY created_at DESC LIMIT 1', params).fetchone()
        return self.public(dict(row)) if row else None

    def pending(self):
        self.expire_pending()
        with connection(self.db_path) as conn:
            return [dict(row) for row in conn.execute("SELECT * FROM approvals WHERE status IN ('pending','approved')")]

    @staticmethod
    def public(request):
        key = json.loads(request['conversation_key_json'])
        return {'id': request['approval_id'], 'run_id': request['run_id'], 'tool_call_id': request['tool_call_id'],
                'tool_name': request['tool_name'], 'arguments': json.loads(request['canonical_arguments_json']),
                'arguments_hash': request['arguments_hash'], 'policy_version': request['policy_version'],
                'status': request['status'], 'created_at': request['created_at'], 'expires_at': request['expires_at'],
                'thread_id': key['thread_id'], 'conversation_key': key}


class ExecutionStore:
    """Claim before executing; never rerun an ambiguous in-flight side effect.

    A crash between a legacy JSON side effect and its terminal write cannot be
    made atomic here. A running claim is intentionally reported as uncertain;
    Database-backed side effects require a transactional execution path to
    remove this uncertainty.
    """
    def __init__(self, db_path):
        self.db_path = db_path

    def get(self, run_id, call):
        apply_migrations(self.db_path)
        with connection(self.db_path) as conn:
            row = conn.execute('SELECT * FROM tool_executions WHERE run_id=? AND tool_call_id=?', (run_id, call['id'])).fetchone()
        if row and row['arguments_hash'] != argument_hash({'name': call['name'], 'arguments': call.get('arguments', {})}):
            raise ValueError('Execution replay changed arguments or tool')
        return dict(row) if row else None

    def claim(self, run_id, call):
        apply_migrations(self.db_path)
        with connection(self.db_path) as conn:
            with conn:
                expected_hash = argument_hash({'name': call['name'], 'arguments': call.get('arguments', {})})
                inserted = conn.execute("INSERT INTO tool_executions(run_id,tool_call_id,arguments_hash,status) VALUES (?,?,?,'running') ON CONFLICT DO NOTHING", (run_id, call['id'], expected_hash)).rowcount == 1
                if not inserted:
                    row = conn.execute('SELECT arguments_hash FROM tool_executions WHERE run_id=? AND tool_call_id=?', (run_id, call['id'])).fetchone()
                    if row['arguments_hash'] != expected_hash:
                        raise ValueError('Execution replay changed arguments or tool')
                return inserted

    def complete(self, run_id, call, result):
        with connection(self.db_path) as conn:
            with conn:
                conn.execute("UPDATE tool_executions SET status=?, result_json=? WHERE run_id=? AND tool_call_id=? AND status='running'", ('failed' if isinstance(result, dict) and 'error' in result else 'completed', canonical_json(result), run_id, call['id']))


approval_store = ApprovalStore()
