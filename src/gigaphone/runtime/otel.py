"""Generic OTel / OpenInference runtime shim — the primitives fixed code calls.

Three primitives, one per fixable failure mode (DESIGN §10):
- ``gigaphone_trace``     — UNTRACED: wrap a boundary in a tool span with complete output.
- ``gigaphone_propagate`` — OFF_CONTEXT: wrap an executor so workers keep the agent context.
- ``gigaphone_complete``  — LOSSY_OUTPUT: add complete output to an existing span.

Vendor-neutral: targets any OTLP backend via the standard OTel context + span APIs. Native
adapters (Braintrust/LangSmith) provide their own shim but the call sites are identical.
"""

from __future__ import annotations

import functools
import json
from collections.abc import Iterable
from typing import Any

from opentelemetry import context as otel_context
from opentelemetry import trace


def _stringify(value: Any) -> str:
    try:
        return json.dumps(value, default=str)
    except (TypeError, ValueError):
        return str(value)


def _resolve(value: Any, field: str) -> Any:
    cur = value
    for part in field.split("."):
        cur = cur.get(part) if isinstance(cur, dict) else getattr(cur, part, None)
    return cur


def _record_output(span, value: Any, fields: Iterable[str]) -> None:
    fields = list(fields)
    if fields:
        for f in fields:
            span.set_attribute(f"gigaphone.output.{f}", _stringify(_resolve(value, f)))
    else:
        span.set_attribute("gigaphone.output", _stringify(value))


def gigaphone_trace(name: str, kind: str = "tool", output: Iterable[str] = ()):
    """Decorator: trace a previously-untraced consumption boundary, recording the complete
    return value. The span opens in the *current* context, so it nests under the agent."""
    fields = tuple(output)

    def deco(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            tracer = trace.get_tracer("gigaphone")
            with tracer.start_as_current_span(name) as span:
                span.set_attribute("gigaphone.kind", kind)
                span.set_attribute("gigaphone.input", _stringify({"args": args, "kwargs": kwargs}))
                result = fn(*args, **kwargs)
                _record_output(span, result, fields)
                return result

        wrapper.__gigaphone_traced__ = True  # type: ignore[attr-defined]
        return wrapper

    return deco


def gigaphone_propagate(executor):
    """Wrap an executor so callables submitted to it run with the submitting thread's OTel
    context attached — re-parenting worker spans under the agent trace (off_context fix)."""
    if getattr(executor, "__gigaphone_propagating__", False):
        return executor
    original_submit = executor.submit

    def submit(fn, /, *args, **kwargs):
        ctx = otel_context.get_current()

        @functools.wraps(fn)
        def run():
            token = otel_context.attach(ctx)
            try:
                return fn(*args, **kwargs)
            finally:
                otel_context.detach(token)

        return original_submit(run)

    executor.submit = submit  # type: ignore[method-assign]
    executor.__gigaphone_propagating__ = True  # type: ignore[attr-defined]
    return executor


def gigaphone_complete(span, value: Any, fields: Iterable[str] = ()) -> None:
    """Record the complete output on an already-open span (lossy_output fix)."""
    _record_output(span, value, fields)
