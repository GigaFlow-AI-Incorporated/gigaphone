"""`gigaphone verify` — run a representative path and confirm tool spans land nested +
complete via the backend adapter's read path (DESIGN §12, ADR-0005)."""

from __future__ import annotations

from gigaphone.core.model import Expectation, VerifyResult


def verify(
    root: str,
    expectations: list[Expectation],
    backend,
    module: str = "app.run_representative",
) -> list[VerifyResult]:
    if not expectations:
        return []
    project_ctx = {"repo": root, "root": root, "module": module}
    return backend.verify(project_ctx, expectations)
