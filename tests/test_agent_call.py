"""agent_call boundary: kind, localization, discovery, resolution, catalog (DESIGN §8.4)."""
from __future__ import annotations

from gigaphone.adapters.backend.otel import OtelAdapter
from gigaphone.core.boundary import BoundaryKind, FailureMode
from gigaphone.core.model import Boundary, Descriptor, Range
from gigaphone.packs.python.pack import PythonPack

_WRAPPER_SRC = '''\
from __future__ import annotations
from subagent_sdk import Runner

def run_subagent(task: str):
    result = Runner.run(task)
    return result
'''


def test_agent_call_kind_value():
    assert BoundaryKind.AGENT_CALL.value == "agent_call"


def test_agent_call_descriptor_localizes_as_untraced_with_agent_emit():
    pack = PythonPack()
    desc = Descriptor(
        id="agent-run_subagent",
        kind=BoundaryKind.AGENT_CALL,
        match_call="harness.run_subagent",
        emit_name="harness.subagent.openai-agents",
    )
    boundaries = pack.analyze("harness.py", _WRAPPER_SRC, [desc])
    assert len(boundaries) == 1
    b = boundaries[0]
    assert b.kind == BoundaryKind.AGENT_CALL
    assert b.failure_modes == [FailureMode.UNTRACED]
    assert b.tools_covered == ["run_subagent"]

    # the UNTRACED fix decorator must declare the span kind as "agent", not "tool"
    prim = OtelAdapter().primitive_for(b, FailureMode.UNTRACED)
    assert 'kind="agent"' in prim.decorator
    assert prim.emit_name == "harness.subagent.openai-agents"
