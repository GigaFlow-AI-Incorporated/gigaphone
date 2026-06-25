"""Native Braintrust backend adapter (DESIGN §9).

Braintrust is in the contextvars-native family, so it reuses the OTel adapter's fix
routing, expectations, and span-file ``verify`` (DESIGN §9: "reuse most fix logic within a
family"). Only the vendor-divergent surface is overridden: SDK detection, config, the init
snippet, and the runtime shim the fixes import (``gigaphone.runtime.braintrust``).

Mapping of the three fixable failure modes to native semantics (via the shim):
- untraced     → ``@traced`` / ``start_span(type="tool")`` around the boundary.
- off_context  → copy the contextvars context into pool workers (Braintrust nests via
                 contextvars and orphans across thread pools).
- lossy_output → ``span.log(output=...)`` with the complete-result fields.
"""

from __future__ import annotations

import os
from dataclasses import replace

from gigaphone.adapters.backend.otel.adapter import OtelAdapter
from gigaphone.core.boundary import FailureMode
from gigaphone.core.model import Boundary, FixPrimitive

_SHIM = "gigaphone.runtime.braintrust"


class BraintrustAdapter(OtelAdapter):
    id = "braintrust"

    def detect_presence(self, repo) -> bool:
        return _scan_for_import(str(repo), "braintrust")

    def config_schema(self) -> dict:
        return {"project": "Braintrust project name", "api_key": "BRAINTRUST_API_KEY"}

    def init_snippet(self, config: dict) -> str:
        project = config.get("project", "${BRAINTRUST_PROJECT}")
        return f"import braintrust\nbraintrust.init_logger(project={project!r})\n"

    def primitive_for(self, boundary: Boundary, mode: FailureMode) -> FixPrimitive:
        # Identical placement + call sites as the OTel family; only the imported shim and the
        # backend id differ (the decorator/wrapper/setter names are shim-agnostic).
        base = super().primitive_for(boundary, mode)
        return replace(
            base,
            backend_id=self.id,
            import_line=base.import_line.replace("gigaphone.runtime.otel", _SHIM),
        )


def _scan_for_import(root: str, marker: str) -> bool:
    for dirpath, _dirs, files in os.walk(root):
        for f in files:
            if not f.endswith(".py"):
                continue
            try:
                with open(os.path.join(dirpath, f), encoding="utf-8") as fh:
                    if marker in fh.read():
                        return True
            except OSError:
                continue
    return False
