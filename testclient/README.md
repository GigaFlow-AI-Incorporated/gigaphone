# testclient — onboarding e2e fixture

A small AI-agent app that stands in for a real customer codebase during GigaPhone's
onboarding flow (DESIGN §14). It is deliberately shaped so the three fixable failure
modes are present *before* GigaPhone runs and gone *after* — which is what makes the
end-to-end test demonstrable (golden principle 5: no fix without a red fixture).

## What's in it

| File | Role | Failure mode (before fix) |
|------|------|---------------------------|
| `app/gateway.py` | a **hand-rolled** `LLMGateway.chat` — no provider SDK | none (already traced; must be *discovered*) |
| `app/exec_tool.py` | `run_code` — collects a complete `ExecResult` on the agent thread | **untraced** (complete output never reaches the trace) |
| `app/web_tools.py` | `web_search` — traced, logs a truncated repr | **lossy_output** |
| `app/web_tools.py` | `fetch_url` — traced *inside a thread-pool worker* | **off_context** (orphan span) |
| `app/agent.py` | the agent loop + the `TOOLS` dispatch registry | — |
| `app/tracing.py` | customer observability (honours `$GIGAPHONE_SPAN_FILE`) | — |
| `app/run_representative.py` | the representative path `verify` runs | — |

The gateway has no recognizable provider SDK, so it is invisible to built-in anchors —
GigaPhone must **discover** it. The agent already has LLM/agent-span visibility; what is
lost is the *tool* output, exactly the situation that blocks activation (DESIGN §1).

## Try it

```bash
TMP=$(mktemp -d); cp -r testclient/app "$TMP/app"
gigaphone onboard --repo "$TMP" --scope app --module app.run_representative
```

Expected report:

```
Harness: cli · Language: python · Backend: otel
3 tools · 1 untraced · 1 off-context · 1 lossy
Fixed + verified 3/3 tool spans (nested + complete).
  ✓ run_code: nested + complete
  ✓ fetch_url: nested + complete
  ✓ web_search: nested + complete
```

The same flow is asserted in `tests/test_e2e_onboarding.py` (red → fix → green →
idempotent) and driven through the MCP server in `tests/test_harness_and_mcp.py`.
