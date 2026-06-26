"""The harness wraps a whole sub-agent. `run_subagent` is the consumption boundary
(kind=agent_call). Before GigaPhone it has no span, so the complete sub-agent result never
reaches the trace — UNTRACED."""
from __future__ import annotations

from wrapper.subagent_sdk import Runner


def run_subagent(task: str):
    result = Runner.run(task)  # dispatch to the black-box sub-agent
    return result
