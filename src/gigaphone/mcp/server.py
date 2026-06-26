"""MCP verifier server — the shared substrate wired into every harness (DESIGN §6).

Exposes the engine verbs as MCP tools so a harness can drive discovery/fix/verify and,
crucially, confirm tool spans land nested + complete (ADR-0005) without leaving the agent.

Import-safe by design: the tool registry and handlers are plain functions (unit-testable
with no MCP dependency). ``serve()`` uses the official ``mcp`` SDK if installed, else a
minimal newline-delimited JSON-RPC stdio loop so the server runs with zero extra deps.
"""

from __future__ import annotations

import json
import sys
from typing import Any

from gigaphone import config
from gigaphone.adapters.registry import select_backend
from gigaphone.engine import detect as _detect
from gigaphone.engine import discover as _discover
from gigaphone.engine import fix as _fix
from gigaphone.engine import verify as _verify
from gigaphone.engine.plan import build_plan

# Tool schema (name -> (description, input keys)). Mirrors the CLI verbs.
TOOLS: dict[str, dict[str, Any]] = {
    "discover": {
        "description": "Propose boundary descriptors and write the config.",
        "input": {"repo": "str", "scope": "str|None"},
    },
    "plan": {
        "description": "Localize boundaries and return plan records + unresolved[].",
        "input": {"repo": "str", "scope": "str|None"},
    },
    "fix": {
        "description": "Apply idempotent codemods; return diffs.",
        "input": {"repo": "str", "scope": "str|None", "apply": "bool"},
    },
    "verify": {
        "description": "Run the representative path; confirm one coherent trace tree — every "
        "LLM and tool span nested + complete, each requested tool linked.",
        "input": {"repo": "str", "module": "str"},
    },
}

# both the LLM gateway and tool boundaries are verified — every call in the agent loop.
_VERIFIABLE = ("tool_exec", "llm")


def call_tool(name: str, args: dict[str, Any]) -> dict[str, Any]:
    """Dispatch an MCP tool call to the engine. Returns a JSON-serializable result."""
    repo = args.get("repo", ".")
    if name == "discover":
        descriptors = _discover.discover(repo, args.get("scope"))
        config.save(repo, descriptors)
        return {"descriptors": [d.to_yaml_obj() for d in descriptors]}
    if name == "plan":
        descriptors = config.load(repo) or _discover.discover(repo, args.get("scope"))
        boundaries = _detect.detect(repo, descriptors, args.get("scope"))
        plan = build_plan(descriptors, boundaries)
        return {
            "records": [r.to_dict() for r in plan.records],
            "unresolved": [u.__dict__ for u in plan.unresolved],
        }
    if name == "fix":
        descriptors = config.load(repo) or _discover.discover(repo, args.get("scope"))
        boundaries = _detect.detect(repo, descriptors, args.get("scope"))
        backend = select_backend(repo)
        if args.get("apply"):
            result = _fix.apply_fixes(repo, boundaries, backend)
            return {"diffs": result.diffs, "skipped_idempotent": result.skipped_idempotent}
        result = _fix.plan_fixes(repo, boundaries, backend)
        return {"would_fix": [e.description for e in result.edits]}
    if name == "verify":
        descriptors = config.load(repo) or _discover.discover(repo, None)
        boundaries = _detect.detect(repo, descriptors, None)
        backend = select_backend(repo)
        expectations = [
            backend.expectation_for(b) for b in boundaries if b.kind.value in _VERIFIABLE
        ]
        tree = _verify.verify_tree(
            repo, expectations, backend, args.get("module", "app.run_representative")
        )
        return {
            "results": [r.__dict__ | {"ok": r.ok} for r in tree.results],
            "single_root": tree.single_root,
            "linkage": [link.__dict__ for link in tree.linkage],
            "ok": tree.ok,
        }
    raise ValueError(f"unknown tool: {name}")


def list_tools() -> list[dict[str, Any]]:
    return [{"name": n, **meta} for n, meta in TOOLS.items()]


def _serve_minimal() -> None:  # pragma: no cover - exercised by integration, not unit tests
    """Newline-delimited JSON-RPC fallback so the server runs with no extra dependency."""
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
            method = req.get("method")
            if method == "tools/list":
                result: Any = list_tools()
            elif method == "tools/call":
                params = req.get("params", {})
                result = call_tool(params["name"], params.get("arguments", {}))
            else:
                result = {"error": f"unknown method {method}"}
            sys.stdout.write(json.dumps({"id": req.get("id"), "result": result}) + "\n")
        except Exception as exc:  # surface loudly
            sys.stdout.write(json.dumps({"error": str(exc)}) + "\n")
        sys.stdout.flush()


def serve() -> None:  # pragma: no cover
    try:
        import mcp  # noqa: F401
    except ImportError:
        _serve_minimal()
        return
    # With the official SDK present, a full server could be wired here; the minimal loop
    # already speaks the same tool contract, so we keep one code path for v1.
    _serve_minimal()


if __name__ == "__main__":  # pragma: no cover
    serve()
