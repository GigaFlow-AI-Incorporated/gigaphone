"""Resolution protocol, config round-trip, and drift detection (DESIGN §5, §8.4, §8.5)."""

from __future__ import annotations

from gigaphone import config
from gigaphone.core.boundary import BoundaryKind
from gigaphone.core.model import Descriptor
from gigaphone.engine.resolve import ingest_resolution


def test_config_round_trips(tmp_path):
    descriptors = [
        Descriptor(
            id="acme-gateway",
            kind=BoundaryKind.LLM,
            match_call="our_llm.chat",
            input_arg="messages",
            output_paths=["response.text"],
            emit_name="acme.llm",
        ),
        Descriptor(
            id="acme-exec",
            kind=BoundaryKind.TOOL_EXEC,
            match_call="sandbox.execute",
            output_paths=["result.stdout", "result.stderr", "result.exit_code"],
            emit_name="acme.exec",
        ),
    ]
    config.save(str(tmp_path), descriptors)
    loaded = config.load(str(tmp_path))
    assert [d.match_call for d in loaded] == ["our_llm.chat", "sandbox.execute"]
    assert loaded[1].output_paths == ["result.stdout", "result.stderr", "result.exit_code"]


def test_resolution_protocol_ingests_and_flags_unresolvable():
    resolution = {
        "resolutions": [
            {
                "id": "exec-dispatch-7",
                "boundary_call": "runner._collect",
                "kind": "tool_exec",
                "complete_output_fields": ["stdout", "stderr", "exit_code"],
                "emit_name": "acme.exec",
            },
            {"id": "mystery-3", "unresolvable": True},
        ]
    }
    descriptors, unresolvable = ingest_resolution(resolution)
    assert len(descriptors) == 1
    assert descriptors[0].match_call == "runner._collect"
    assert descriptors[0].output_paths == ["stdout", "stderr", "exit_code"]
    assert unresolvable == ["mystery-3"]  # surfaced, never silently dropped (golden principle 8)


def test_drift_when_a_committed_anchor_no_longer_resolves():
    descriptors = [
        Descriptor(id="a", kind=BoundaryKind.TOOL_EXEC, match_call="app.tools.run_code"),
        Descriptor(id="b", kind=BoundaryKind.TOOL_EXEC, match_call="app.tools.gone"),
    ]
    resolved = {"app.tools.run_code"}  # only one still resolves
    drift = config.detect_drift(descriptors, resolved)
    assert drift == ["app.tools.gone"]
