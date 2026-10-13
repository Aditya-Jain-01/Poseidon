"""Run Person 1 checks with temporary storage and the invoking interpreter.

This is the M0-M2 verification helper, not the final M7 release gate.
"""
from pathlib import Path
import argparse
import hashlib
import os
import subprocess
import sys
import tempfile

PROJECT = Path(__file__).resolve().parents[2]


def hashes():
    root = PROJECT / 'memory-store'
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob('*') if p.is_file()}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--full', action='store_true', help='Run the entire backend suite, including documented deferred failures')
    args = parser.parse_args()
    if sys.version_info < (3, 11):
        raise SystemExit('Python 3.11+ is required')
    before = hashes()
    with tempfile.TemporaryDirectory(prefix='poseidon-person1-') as tmp:
        env = dict(os.environ)
        env.update(POSEIDON_DB_PATH=str(Path(tmp) / 'state.db'), AGENTS_DIR=str(Path(tmp) / 'agents'), LLM_CONFIG_PATH=str(Path(tmp) / 'llm.json'), TELEGRAM_POLLING_ENABLED='false', HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', TMP=tmp, TEMP=tmp, TMPDIR=tmp)
        suites = ['backend/tests'] if args.full else [f'backend/tests/{name}' for name in ('test_foundation.py', 'test_identity_contract.py', 'test_durable_runtime.py', 'test_harness_approval_resumption.py')]
        result = subprocess.run([sys.executable, '-m', 'pytest', *suites, '-q', '-o', 'asyncio_mode=auto', '-o', 'pythonpath=backend', '--basetemp', str(Path(tmp) / 'pytest')], cwd=PROJECT, env=env)
    if hashes() != before:
        print('FAIL: real memory-store changed', file=sys.stderr)
        return 1
    print('Real memory-store hashes unchanged')
    return result.returncode


if __name__ == '__main__':
    raise SystemExit(main())
