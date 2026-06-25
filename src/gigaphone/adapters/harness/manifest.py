"""One source of truth for both harness manifests (DESIGN §6).

The divergent bits across harnesses are the manifest format and the hook format; the
SKILL.md body, MCP server, language packs, codemods, and plan records are all shared. So
we keep a single ``PLUGIN`` spec and render it per harness.

The repo root is itself the Claude Code plugin **and** a single-plugin marketplace, so the
cloned engine is reachable from ``${CLAUDE_PLUGIN_ROOT}`` — the MCP server and the post-edit
hook launch it with ``uv`` (no separate install step). Hooks are plain shell commands
(Codex runs command hooks only), so the same command works on both harnesses.

``scripts/build_plugins.py`` writes the committed plugin files from these renders.
"""

from __future__ import annotations

from typing import Any

NAME = "gigaphone"
VERSION = "0.5.0"
DESCRIPTION = (
    "Trace-coverage instrumentation for AI agent tool executions — "
    "neutral across harness, language, vendor, and codebase."
)

# The engine is launched from the cloned plugin via uv, so installing the plugin needs no
# separate `pip install` (only uv on PATH). ${CLAUDE_PLUGIN_ROOT} is the plugin dir (= repo
# root); ${CLAUDE_PROJECT_DIR} is the user's project where the hook should run.
_MCP_COMMAND = "uv"
_MCP_ARGS = ["run", "--project", "${CLAUDE_PLUGIN_ROOT}", "gigaphone-mcp"]
_HOOK_COMMAND = (
    'uv run --project "${CLAUDE_PLUGIN_ROOT}" gigaphone detect '
    '--repo "${CLAUDE_PROJECT_DIR}" || true'
)

# The single source. Adding a harness = a new render_* function, not a new copy of this.
PLUGIN: dict[str, Any] = {
    "name": NAME,
    "version": VERSION,
    "description": DESCRIPTION,
    "mcp_server": {"command": _MCP_COMMAND, "args": _MCP_ARGS},
    "hook_command": _HOOK_COMMAND,
}


def render_claude_code() -> dict[str, Any]:
    """Claude Code: a repo-root plugin (`.claude-plugin/plugin.json`) that is also a
    single-plugin marketplace, with a bundled skill and a post-edit hook."""
    return {
        # plugin.json declares only identity. The standard component dirs (skills/,
        # hooks/hooks.json) and .mcp.json auto-load — declaring them too is a duplicate.
        "plugin.json": {
            "name": NAME,
            "version": VERSION,
            "description": DESCRIPTION,
            "author": {"name": "Gigaflow"},
        },
        ".mcp.json": {"mcpServers": {NAME: PLUGIN["mcp_server"]}},
        "marketplace.json": {
            "name": NAME,
            "owner": {"name": "Gigaflow"},
            "description": "GigaPhone — trace-coverage instrumentation for AI agent codebases.",
            "plugins": [{"name": NAME, "source": ".", "description": DESCRIPTION}],
        },
        # hooks/hooks.json wraps the hook map under a top-level "hooks" key.
        "hooks.json": {
            "hooks": {
                "PostToolUse": [
                    {
                        "matcher": "Edit|Write",
                        "hooks": [{"type": "command", "command": _HOOK_COMMAND}],
                    }
                ]
            }
        },
    }


def render_codex() -> dict[str, Any]:
    """Codex: a plugin manifest (+ agents/openai.yaml) + command-only hooks. Codex discovers
    the shared skill via the repo's `.agents/skills/gigaphone/` directly."""
    return {
        "plugin.toml": {
            "name": NAME,
            "version": VERSION,
            "description": DESCRIPTION,
            "mcp_servers": {NAME: PLUGIN["mcp_server"]},
        },
        "openai.yaml": {
            "interface": {"display_name": "GigaPhone", "short_description": DESCRIPTION},
            "policy": {"allow_implicit_invocation": True},
        },
        # Codex runs command hooks only — the same plain shell command.
        "hooks": [{"on": "post-edit", "run": _HOOK_COMMAND}],
    }
