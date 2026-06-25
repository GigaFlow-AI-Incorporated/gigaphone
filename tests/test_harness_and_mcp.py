"""Harness axis + MCP substrate (DESIGN §6).

Both harness manifests must derive from one source (no drift), and the MCP server must
drive the engine end-to-end — including the verify that proves spans land nested + complete.
"""

from __future__ import annotations

import os
import shutil

import pytest

from gigaphone.adapters.harness.claude_code import ClaudeCodeAdapter
from gigaphone.adapters.harness.codex import CodexAdapter
from gigaphone.adapters.harness.manifest import PLUGIN, render_claude_code, render_codex
from gigaphone.mcp import server

_TESTCLIENT = os.path.join(os.path.dirname(__file__), "..", "testclient", "app")


def test_both_manifests_come_from_one_source():
    cc = render_claude_code()
    cx = render_codex()
    # same identity + MCP server + hook command, rendered into each harness's format
    assert cc["plugin.json"]["name"] == cx["plugin.toml"]["name"] == PLUGIN["name"]
    assert (
        cc["plugin.json"]["mcpServers"]["gigaphone"]
        == cx["plugin.toml"]["mcp_servers"]["gigaphone"]
    )
    cc_cmd = cc["settings.hooks"]["PostToolUse"][0]["hooks"][0]["command"]
    cx_cmd = cx["hooks"][0]["run"]
    assert cc_cmd == cx_cmd == PLUGIN["hooks"][0]["command"]


def test_codex_runs_command_only_hooks():
    cx = render_codex()
    # Codex hooks are plain shell commands (no event-object form)
    assert set(cx["hooks"][0]) == {"on", "run"}
    assert "agents/openai.yaml" in cx


def test_adapters_implement_the_interface_and_decline_to_drive():
    for adapter in (ClaudeCodeAdapter(), CodexAdapter()):
        assert adapter.skill_frontmatter()["name"] == "gigaphone"
        assert adapter.package()  # renders a manifest
        with pytest.raises(NotImplementedError):
            adapter.drive("any task")  # the engine never calls a model (ADR-0006)


def test_mcp_exposes_engine_verbs():
    names = {t["name"] for t in server.list_tools()}
    assert {"discover", "plan", "fix", "verify"} <= names


def test_mcp_drives_full_onboarding_end_to_end(tmp_path):
    shutil.copytree(_TESTCLIENT, tmp_path / "app")
    repo = str(tmp_path)

    discovered = server.call_tool("discover", {"repo": repo, "scope": "app"})
    assert any(d["kind"] == "llm" for d in discovered["descriptors"])

    plan = server.call_tool("plan", {"repo": repo, "scope": "app"})
    modes = {m for r in plan["records"] for m in r["failure_modes"]}
    assert {"untraced", "off_context", "lossy_output"} <= modes

    server.call_tool("fix", {"repo": repo, "scope": "app", "apply": True})

    verified = server.call_tool("verify", {"repo": repo, "module": "app.run_representative"})
    assert verified["results"] and all(r["ok"] for r in verified["results"])
