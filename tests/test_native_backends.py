"""Native backend adapters (Braintrust + LangSmith) — contextvars-native family.

These import cleanly without the vendor SDKs installed; the runtime shims import the SDK
lazily and degrade to the OTel primitives when it is absent (so fixed code still runs and
stays verifiable in CI).
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

import pytest

from gigaphone.adapters.backend.braintrust import BraintrustAdapter
from gigaphone.adapters.backend.langsmith import LangSmithAdapter
from gigaphone.core.boundary import BoundaryKind, FailureMode
from gigaphone.core.model import Boundary, Range
from gigaphone.runtime import braintrust as bt_shim
from gigaphone.runtime import langsmith as ls_shim


def _boundary() -> Boundary:
    return Boundary(
        descriptor_id="tool-run",
        kind=BoundaryKind.TOOL_EXEC,
        path="app/x.py",
        func_name="run",
        call="app.x.run",
        range=Range("app/x.py", 0, 10, 1),
        complete_output_fields=["stdout", "stderr", "exit_code"],
        tools_covered=["run"],
        emit_name="app.run",
        existing_span_name="run",
    )


@pytest.mark.parametrize(
    ("adapter_cls", "shim_module"),
    [
        (BraintrustAdapter, "gigaphone.runtime.braintrust"),
        (LangSmithAdapter, "gigaphone.runtime.langsmith"),
    ],
)
def test_primitive_for_all_modes_points_at_native_shim(adapter_cls, shim_module):
    adapter = adapter_cls()
    b = _boundary()

    untraced = adapter.primitive_for(b, FailureMode.UNTRACED)
    assert untraced.backend_id == adapter.id
    assert untraced.import_line == f"from {shim_module} import gigaphone_trace"
    assert untraced.decorator and "gigaphone_trace(" in untraced.decorator

    off_ctx = adapter.primitive_for(b, FailureMode.OFF_CONTEXT)
    assert off_ctx.import_line == f"from {shim_module} import gigaphone_propagate"
    assert off_ctx.executor_wrapper == "gigaphone_propagate"

    lossy = adapter.primitive_for(b, FailureMode.LOSSY_OUTPUT)
    assert lossy.import_line == f"from {shim_module} import gigaphone_complete"
    assert lossy.attr_setter_template and "gigaphone_complete(" in lossy.attr_setter_template


@pytest.mark.parametrize("adapter_cls", [BraintrustAdapter, LangSmithAdapter])
def test_expectations_reuse_the_family_keys(adapter_cls):
    b = _boundary()
    b.failure_modes = [FailureMode.UNTRACED]
    b.requires_complete_attrs = True
    b.existing_span_name = None  # an untraced boundary has no existing span; it gets emit_name
    exp = adapter_cls().expectation_for(b)
    assert exp.span_name == "app.run"
    assert exp.require_attrs == [
        "gigaphone.output.stdout",
        "gigaphone.output.stderr",
        "gigaphone.output.exit_code",
    ]


def test_detect_presence_scans_for_the_sdk_import(tmp_path):
    (tmp_path / "uses_bt.py").write_text("import braintrust\n")
    (tmp_path / "uses_ls.py").write_text("from langsmith import traceable\n")
    assert BraintrustAdapter().detect_presence(str(tmp_path)) is True
    assert LangSmithAdapter().detect_presence(str(tmp_path)) is True

    other = tmp_path / "sub"
    other.mkdir()
    (other / "plain.py").write_text("import os\n")
    assert BraintrustAdapter().detect_presence(str(other)) is False
    assert LangSmithAdapter().detect_presence(str(other)) is False


@pytest.mark.parametrize("shim", [bt_shim, ls_shim])
def test_shim_imports_lazily_and_falls_back_without_sdk(shim):
    # The vendor SDKs are not installed in CI -> the lazy probe returns None and the shim
    # degrades to the OTel primitives. The call sites must still work.
    @shim.gigaphone_trace(name="t", output=["value"])
    def f(x):
        return {"value": x, "extra": "dropped"}

    assert f(7) == {"value": 7, "extra": "dropped"}  # decorator is transparent to the result

    with ThreadPoolExecutor(max_workers=2) as ex:
        wrapped = shim.gigaphone_propagate(ex)
        assert wrapped.submit(lambda: 21).result() == 21
        # idempotent: wrapping twice does not double-wrap
        assert shim.gigaphone_propagate(wrapped) is wrapped

    captured = {}

    class _FakeOtelSpan:
        def set_attribute(self, k, v):
            captured[k] = v

    shim.gigaphone_complete(_FakeOtelSpan(), {"value": 1}, fields=["value"])
    assert captured.get("gigaphone.output.value") == "1"
