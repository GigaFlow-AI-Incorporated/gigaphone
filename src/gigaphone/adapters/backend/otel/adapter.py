"""Generic OTel / OpenInference backend adapter (DESIGN §9).

The two-tier default: targets any OTLP backend with no code change (new platform =
endpoint + headers). Supplies the vendor-specific *pieces* of each fix (which import,
which decorator/wrapper/setter); the language pack decides placement. ``verify`` reads the
exported spans — the same read path the eval platform uses (DESIGN §12, ADR-0005).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile

from gigaphone.core.boundary import BoundaryKind, FailureMode
from gigaphone.core.model import Boundary, Expectation, FixPrimitive, VerifyResult
from gigaphone.interfaces.backend_adapter import BackendAdapter

_SHIM = "gigaphone.runtime.otel"


class OtelAdapter(BackendAdapter):
    id = "otel"

    # --- detection / config ---------------------------------------------------------
    def detect_presence(self, repo) -> bool:
        root = str(repo)
        for dirpath, _dirs, files in os.walk(root):
            if any(f.endswith(".py") for f in files):
                for f in files:
                    if not f.endswith(".py"):
                        continue
                    try:
                        with open(os.path.join(dirpath, f), encoding="utf-8") as fh:
                            text = fh.read()
                    except OSError:
                        continue
                    if "opentelemetry" in text or "openinference" in text:
                        return True
        return False

    def config_schema(self) -> dict:
        return {
            "endpoint": "OTLP endpoint URL",
            "headers": "OTLP headers (auth)",
            "service_name": "logical service name",
        }

    def init_snippet(self, config: dict) -> str:
        ep = config.get("endpoint", "${OTEL_EXPORTER_OTLP_ENDPOINT}")
        return (
            "from opentelemetry import trace\n"
            "from opentelemetry.sdk.trace import TracerProvider\n"
            "from opentelemetry.sdk.trace.export import BatchSpanProcessor\n"
            "from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter\n"
            "provider = TracerProvider()\n"
            f"provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint={ep!r})))\n"
            "trace.set_tracer_provider(provider)\n"
        )

    # --- fix primitives (one per failure mode) --------------------------------------
    def primitive_for(self, boundary: Boundary, mode: FailureMode) -> FixPrimitive:
        if mode == FailureMode.UNTRACED:
            name = boundary.emit_name or f"{boundary.provider_or_framework}.{boundary.func_name}"
            fields = ", ".join(repr(f) for f in boundary.complete_output_fields)
            span_kind = "agent" if boundary.kind == BoundaryKind.AGENT_CALL else "tool"
            decorator = f'gigaphone_trace(name="{name}", kind="{span_kind}", output=[{fields}])'
            return FixPrimitive(
                failure_mode=mode,
                backend_id=self.id,
                import_line=f"from {_SHIM} import gigaphone_trace",
                emit_name=name,
                output_fields=tuple(boundary.complete_output_fields),
                decorator=decorator,
            )
        if mode == FailureMode.OFF_CONTEXT:
            return FixPrimitive(
                failure_mode=mode,
                backend_id=self.id,
                import_line=f"from {_SHIM} import gigaphone_propagate",
                emit_name=boundary.existing_span_name or boundary.func_name,
                executor_wrapper="gigaphone_propagate",
            )
        if mode == FailureMode.LOSSY_OUTPUT:
            return FixPrimitive(
                failure_mode=mode,
                backend_id=self.id,
                import_line=f"from {_SHIM} import gigaphone_complete",
                emit_name=boundary.existing_span_name or boundary.func_name,
                output_fields=tuple(boundary.complete_output_fields),
                attr_setter_template="gigaphone_complete({span}, {value}, fields={fields})",
            )
        raise ValueError(f"no OTel primitive for {mode} (introduce-a-boundary is advisory)")

    def expectation_for(self, boundary: Boundary) -> Expectation:
        """What this boundary's span must look like post-fix — derivable whether or not the
        boundary still carries a failure mode, so ``verify`` is stateless (ADR-0005)."""
        tool = boundary.tools_covered[0] if boundary.tools_covered else boundary.func_name
        span_name = boundary.existing_span_name or boundary.emit_name or boundary.func_name
        if boundary.kind == BoundaryKind.AGENT_CALL:
            # native body-wrap: assert the dispatch span is present + nested under the agent
            # root; a streamed dispatch has no single return to assert completeness on.
            return Expectation(tool, span_name, require_nested=True, require_attrs=[])
        attrs = (
            [f"gigaphone.output.{f}" for f in boundary.complete_output_fields]
            if boundary.requires_complete_attrs
            else []
        )
        return Expectation(tool, span_name, require_nested=True, require_attrs=attrs)

    # fix-primitive methods required by the interface (delegate to primitive_for/emitter) ---
    def trace_boundary(self, node, kind):  # pragma: no cover - covered via primitive_for
        return self.primitive_for(node, FailureMode.UNTRACED)

    def restore_context(self):  # pragma: no cover
        return "gigaphone_propagate"

    def map_output(self, output_spec):  # pragma: no cover
        return output_spec

    def enable_framework(self, framework):  # pragma: no cover
        return None

    # --- verification (the read path the eval platform uses) ------------------------
    def verify(self, project, run) -> list[VerifyResult]:
        """project = {"repo": dir, "module": "app.run_representative", "root": dir}
        run = list[Expectation]. Runs the representative path, captures spans, checks each
        expected tool span is present, nested under the agent root, and complete."""
        repo = project["repo"]
        module = project.get("module", "app.run_representative")
        root = project.get("root", repo)
        expectations: list[Expectation] = run

        spans = _run_and_capture(repo, root, module)
        by_id = {s["span_id"]: s for s in spans}
        roots = [s for s in spans if s.get("parent_id") is None]
        agent = next((s for s in roots if s["name"] == "agent"), roots[0] if roots else None)
        agent_id = agent["span_id"] if agent else None

        results: list[VerifyResult] = []
        for exp in expectations:
            matches = [s for s in spans if s["name"] == exp.span_name]
            if not matches:
                results.append(VerifyResult(exp.tool, False, False, False, "span not found"))
                continue
            span = matches[-1]
            nested = (not exp.require_nested) or _is_descendant(span, agent_id, by_id)
            missing = [a for a in exp.require_attrs if a not in span.get("attributes", {})]
            complete = not missing
            problems = []
            if not nested:
                problems.append("orphan")
            if missing:
                problems.append("missing " + ",".join(missing))
            results.append(VerifyResult(exp.tool, True, nested, complete, " ".join(problems)))
        return results


def _is_descendant(span: dict, ancestor_id, by_id: dict) -> bool:
    seen = set()
    cur = span
    while cur is not None and cur["span_id"] not in seen:
        seen.add(cur["span_id"])
        pid = cur.get("parent_id")
        if pid == ancestor_id:
            return True
        cur = by_id.get(pid)
    return False


def _run_and_capture(repo: str, root: str, module: str) -> list[dict]:
    fd, span_file = tempfile.mkstemp(suffix=".jsonl", prefix="gigaphone_spans_")
    os.close(fd)
    open(span_file, "w").close()
    env = dict(os.environ)
    env["GIGAPHONE_SPAN_FILE"] = span_file
    env["PYTHONPATH"] = os.pathsep.join(filter(None, [root, env.get("PYTHONPATH", "")]))
    proc = subprocess.run(
        [sys.executable, "-m", module],
        cwd=repo,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"representative path failed:\n{proc.stderr}")
    spans = []
    with open(span_file, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                spans.append(json.loads(line))
    os.unlink(span_file)
    return spans
