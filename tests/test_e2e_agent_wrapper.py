"""E2E: a harness that wraps a whole sub-agent. The agent_call boundary is UNTRACED before
GigaPhone and traced + complete + nested after (DESIGN §3, §10; spec 2026-06-26)."""
from __future__ import annotations

import os
import shutil

import pytest

from gigaphone import config
from gigaphone.adapters.backend.otel import OtelAdapter
from gigaphone.core.boundary import BoundaryKind, FailureMode
from gigaphone.engine import detect as _detect
from gigaphone.engine import discover as _discover
from gigaphone.engine import fix as _fix
from gigaphone.engine import verify as _verify

_TESTCLIENT = os.path.join(os.path.dirname(__file__), "..", "testclient", "wrapper")


@pytest.fixture
def repo(tmp_path):
    shutil.copytree(_TESTCLIENT, tmp_path / "wrapper")
    return str(tmp_path)


def test_agent_wrapper_red_then_green_then_idempotent(repo):
    backend = OtelAdapter()
    descs = _discover.discover(repo, "wrapper")
    # discovery recognized the sub-agent dispatch
    agent = next((d for d in descs if d.kind == BoundaryKind.AGENT_CALL), None)
    assert agent is not None and agent.match_call == "wrapper.harness.run_subagent"

    config.save(repo, descs)
    boundaries = _detect.detect(repo, descs, "wrapper")
    run_b = next(b for b in boundaries if b.func_name == "run_subagent")
    assert run_b.failure_modes == [FailureMode.UNTRACED]

    expectations = [backend.expectation_for(b) for b in boundaries if b.failure_modes]

    # RED: the sub-agent dispatch has no span yet
    before = _verify.verify(repo, expectations, backend, "wrapper.run_representative")
    assert not all(v.ok for v in before)

    # FIX
    result = _fix.apply_fixes(repo, boundaries, backend)
    assert result.diffs

    # GREEN: the agent_call span is now present, nested under the agent root, complete
    after = _verify.verify(repo, expectations, backend, "wrapper.run_representative")
    assert all(v.ok for v in after), [(v.tool, v.detail) for v in after]

    # the emitted span declares kind=agent
    harness_src = open(os.path.join(repo, "wrapper", "harness.py"), encoding="utf-8").read()
    assert 'kind="agent"' in harness_src

    # IDEMPOTENT
    boundaries2 = _detect.detect(repo, descs, "wrapper")
    rerun = _fix.apply_fixes(repo, boundaries2, backend)
    assert not rerun.diffs
