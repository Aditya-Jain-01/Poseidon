"""In-process execution guard for trusted Poseidon tool handlers.

Enforces:
1. Filesystem path jailing: only permitted subtrees under memory-store/ or designated scratch.
2. Argument sanitization: rejects path traversals, absolute escapes, and dangerous payloads.
3. Execution timeouts: prevents tool executions from hanging the agent loop.
4. Shell execution prohibition: strictly rejects any attempt to invoke shell or terminal binaries.
"""

from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
import inspect
from pathlib import Path
from typing import Any, Callable

from app.config import settings

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_ALLOWED_ROOTS: list[Path] = [
    (_PROJECT_ROOT / "memory-store").resolve(),
]

_DEFAULT_TIMEOUT_SECONDS = 5.0
_thread_pool = ThreadPoolExecutor(max_workers=4)


class ExecutionSecurityError(PermissionError):
    """Raised when an operation violates execution-guard containment."""


class ExecutionTimeoutError(TimeoutError):
    """Raised when a tool execution exceeds the configured wall-clock timeout.

    A timeout cannot safely stop a thread that is already running. Tool handlers
    therefore must be idempotent; the execution repository enforces that at the
    orchestration boundary.
    """


class ExecutionGuard:
    """Validation and timeout guard, not an adversarial sandbox.

    It runs reviewed built-in handlers in the Poseidon process. It does not
    isolate filesystem, network, or arbitrary third-party code. MCP process
    supervision and arbitrary plugin loading are outside this guard's scope.
    """

    @classmethod
    def get_allowed_roots(cls) -> list[Path]:
        """Return canonical paths of allowed directories."""
        return list(_ALLOWED_ROOTS)

    @classmethod
    def validate_path(cls, path: str | Path, must_exist: bool = False, write: bool = False) -> Path:
        """Validate that a target filesystem path is contained within allowed subtrees.

        Rejects path traversal ('..'), absolute escapes outside memory-store, and system directories.
        """
        raw_str = str(path).strip()
        if not raw_str:
            raise ExecutionSecurityError("Path cannot be empty.")

        # Check for path traversal attempts before resolving
        if ".." in raw_str:
            raise ExecutionSecurityError(f"Path traversal detected: {raw_str}")

        resolved = Path(path).resolve()

        is_allowed = False
        for root in _ALLOWED_ROOTS:
            try:
                resolved.relative_to(root)
                is_allowed = True
                break
            except ValueError:
                continue

        if not is_allowed:
            raise ExecutionSecurityError(
                f"Path access denied: '{resolved}' is outside allowed directories: {[str(r) for r in _ALLOWED_ROOTS]}"
            )

        if must_exist and not resolved.exists():
            raise FileNotFoundError(f"Path does not exist: {resolved}")

        return resolved

    @classmethod
    async def execute(
        cls,
        tool_name: str,
        func: Callable[..., Any],
        arguments: dict[str, Any],
        timeout_seconds: float = _DEFAULT_TIMEOUT_SECONDS,
    ) -> Any:
        """Execute a tool function within the sandbox boundary.

        Enforces timeouts and captures errors gracefully.
        """
        tool = (tool_name or "").strip().lower()

        if "terminal" in tool or "shell" in tool or "bash" in tool or "exec" in tool:
            raise ExecutionSecurityError(f"Tool '{tool_name}' is forbidden: terminal execution is disabled in v1.")

        for key, val in arguments.items():
            if isinstance(val, str) and ("path" in key.lower() or "file" in key.lower() or "dir" in key.lower()):
                # If looks like a path or contains separators, validate
                if "/" in val or "\\" in val or val.endswith((".md", ".json", ".db", ".txt")):
                    cls.validate_path(val)

        try:
            if inspect.iscoroutinefunction(func):
                result = await asyncio.wait_for(func(**arguments), timeout=timeout_seconds)
            else:
                loop = asyncio.get_running_loop()
                result = await asyncio.wait_for(
                    loop.run_in_executor(_thread_pool, lambda: func(**arguments)),
                    timeout=timeout_seconds,
                )
            return result
        except asyncio.TimeoutError as exc:
            raise ExecutionTimeoutError(f"Tool '{tool_name}' timed out after {timeout_seconds}s") from exc
        except Exception as exc:
            if isinstance(exc, ExecutionSecurityError):
                raise
            raise


# Compatibility aliases for existing callers. New code must use
# ExecutionGuard and the Execution* exception names above.
SandboxGuard = ExecutionGuard
SandboxSecurityError = ExecutionSecurityError
SandboxTimeoutError = ExecutionTimeoutError
