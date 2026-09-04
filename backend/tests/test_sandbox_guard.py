"""Tests for SandboxGuard capability boundaries."""

import asyncio
import pytest
from pathlib import Path
from app.security.sandbox import SandboxGuard, SandboxSecurityError, SandboxTimeoutError


def test_sandbox_path_validation_allowed():
    roots = SandboxGuard.get_allowed_roots()
    assert len(roots) > 0
    valid_path = roots[0] / "skills" / "test_skill.SKILL.md"
    validated = SandboxGuard.validate_path(valid_path)
    assert validated == valid_path.resolve()


def test_sandbox_path_validation_rejects_traversal():
    with pytest.raises(SandboxSecurityError, match="Path traversal detected"):
        SandboxGuard.validate_path("../../etc/passwd")


def test_sandbox_path_validation_rejects_outside_escape():
    with pytest.raises(SandboxSecurityError, match="outside allowed directories"):
        SandboxGuard.validate_path("C:/Windows/System32/calc.exe")


@pytest.mark.asyncio
async def test_sandbox_rejects_terminal_tool():
    async def dummy_exec():
        return "ran"

    with pytest.raises(SandboxSecurityError, match="terminal execution is disabled"):
        await SandboxGuard.execute("terminal_exec", dummy_exec, {})


@pytest.mark.asyncio
async def test_sandbox_enforces_execution_timeout():
    async def slow_tool():
        await asyncio.sleep(0.5)
        return "done"

    with pytest.raises(SandboxTimeoutError, match="timed out"):
        await SandboxGuard.execute("slow_tool", slow_tool, {}, timeout_seconds=0.1)


@pytest.mark.asyncio
async def test_sandbox_executes_valid_tool():
    def sync_tool(x: int, y: int):
        return x + y

    res = await SandboxGuard.execute("add", sync_tool, {"x": 2, "y": 3})
    assert res == 5
