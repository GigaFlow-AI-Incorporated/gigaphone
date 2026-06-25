"""Native LangSmith backend adapter (DESIGN §9).

LangSmith is in the contextvars-native family, so it reuses the OTel adapter's fix routing,
expectations, and span-file ``verify`` (DESIGN §9: "reuse most fix logic within a family").
Only the vendor-divergent surface is overridden: SDK detection, config, the init snippet,
and the runtime shim the fixes import (``gigaphone.runtime.langsmith``).

Mapping of the three fixable failure modes to native semantics (via the shim):
- untraced     → ``@traceable(run_type="tool")`` around the boundary.
- off_context  → copy the contextvars context into pool workers (LangSmith nests via
                 contextvars / the current ``RunTree`` and orphans across thread pools).
- lossy_output → ``RunTree.add_metadata`` with the complete-result fields.
"""

from __future__ import annotations

import os
from dataclasses import replace

from gigaphone.adapters.backend.otel.adapter import OtelAdapter
from gigaphone.core.boundary import FailureMode
from gigaphone.core.model import Boundary, FixPrimitive

_SHIM = "gigaphone.runtime.langsmith"


class LangSmithAdapter(OtelAdapter):
    id = "langsmith"

    def detect_presence(self, repo) -> bool:
        return _scan_for_import(str(repo), "langsmith")

    def config_schema(self) -> dict:
        return {"project": "LANGCHAIN_PROJECT", "api_key": "LANGCHAIN_API_KEY"}

    def init_snippet(self, config: dict) -> str:
        return (
            "import langsmith  # tracing is enabled via LANGCHAIN_TRACING_V2=true\n"
            "_ls_client = langsmith.Client()\n"
        )

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
