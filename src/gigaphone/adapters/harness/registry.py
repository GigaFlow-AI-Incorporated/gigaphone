"""Harness-adapter registry. New harness = register an adapter; everything else is shared."""

from __future__ import annotations

from gigaphone.adapters.harness.claude_code import ClaudeCodeAdapter
from gigaphone.adapters.harness.codex import CodexAdapter
from gigaphone.interfaces.harness_adapter import HarnessAdapter

_HARNESSES: dict[str, HarnessAdapter] = {
    "claude-code": ClaudeCodeAdapter(),
    "codex": CodexAdapter(),
}


def harness_by_id(harness_id: str) -> HarnessAdapter | None:
    return _HARNESSES.get(harness_id)


def all_harnesses() -> list[HarnessAdapter]:
    return list(_HARNESSES.values())
