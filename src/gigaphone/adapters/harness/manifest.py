"""One source of truth for both harness manifests (DESIGN §6).

The divergent bits across harnesses are the manifest format and the hook format; the
SKILL.md body, MCP server, language packs, codemods, and plan records are all shared. So
we keep a single ``PLUGIN`` spec and render it per harness. Hooks are plain shell commands
(Codex runs command hooks only), so the same hook command works everywhere.
"""

from __future__ import annotations

from typing import Any

# The single source. Adding a harness = a new render_* function, not a new copy of this.
PLUGIN: dict[str, Any] = {
    "name": "gigaphone",
    "version": "0.5.0",
    "description": "Trace-coverage instrumentation for AI agent tool executions — "
    "neutral across harness, language, vendor, and codebase.",
    "skill": ".agents/skills/gigaphone/SKILL.md",
    "commands": ["discover", "detect", "plan", "resolve", "fix", "verify", "onboard"],
    # MCP verifier — the shared substrate across harnesses (DESIGN §6).
    "mcp_server": {"command": "python", "args": ["-m", "gigaphone.mcp.server"]},
    # post-edit hook: keep coverage from regressing as code changes (plain shell command).
    "hooks": [
        {
            "event": "post-edit",
            "command": "gigaphone detect --repo . || true",
        }
    ],
}


def render_claude_code() -> dict[str, Any]:
    """Claude Code plugin manifest + marketplace entry + event-hook settings."""
    p = PLUGIN
    return {
        "plugin.json": {
            "name": p["name"],
            "version": p["version"],
            "description": p["description"],
            "mcpServers": {p["name"]: p["mcp_server"]},
        },
        "marketplace_entry": {
            "name": p["name"],
            "source": "./",
            "description": p["description"],
        },
        # Claude Code supports event hooks (PostToolUse).
        "settings.hooks": {
            "PostToolUse": [
                {
                    "matcher": "Edit|Write",
                    "hooks": [{"type": "command", "command": h["command"]}],
                }
                for h in p["hooks"]
            ]
        },
    }


def render_codex() -> dict[str, Any]:
    """Codex plugin manifest (+ agents/openai.yaml) + command-only hooks."""
    p = PLUGIN
    return {
        "plugin.toml": {
            "name": p["name"],
            "version": p["version"],
            "description": p["description"],
            "mcp_servers": {p["name"]: p["mcp_server"]},
        },
        "agents/openai.yaml": {
            "interface": {"display_name": "GigaPhone", "short_description": p["description"]},
            "policy": {"allow_implicit_invocation": True},
        },
        # Codex runs command hooks only — the same plain shell command.
        "hooks": [{"on": "post-edit", "run": h["command"]} for h in p["hooks"]],
    }
