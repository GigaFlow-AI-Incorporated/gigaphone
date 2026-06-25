"""Harness adapters (the harness axis, DESIGN §6).

The entire harness-specific surface; everything else is shared. Both v1 harness manifests
are generated from ONE source (``manifest.py``) so they never drift (harness-engineering:
generate both manifests from one source).
"""

from gigaphone.adapters.harness.claude_code import ClaudeCodeAdapter
from gigaphone.adapters.harness.codex import CodexAdapter

__all__ = ["ClaudeCodeAdapter", "CodexAdapter"]
