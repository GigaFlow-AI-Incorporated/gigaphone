"""Representative path GigaPhone runs during `verify`: a root `agent` span that dispatches
the sub-agent once, so the adapter can confirm the agent_call span is nested + complete."""
from __future__ import annotations

from wrapper.harness import run_subagent
from wrapper.tracing import init_tracing, tracer


def main() -> str:
    init_tracing()
    with tracer().start_as_current_span("agent") as span:
        span.set_attribute("agent.task", "delegate to sub-agent")
        result = run_subagent("summarize the repo")
        span.set_attribute("agent.final", result.final_output)
        return result.final_output


if __name__ == "__main__":
    main()
