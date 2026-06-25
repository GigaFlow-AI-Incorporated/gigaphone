"""`gigaphone resolve` — ingest a harness-supplied resolution for unresolved boundaries
(DESIGN §5 resolution protocol). Schema-validated; an unresolvable item is reported, never
silently dropped (golden principle 8)."""

from __future__ import annotations

from gigaphone.core.boundary import BoundaryKind
from gigaphone.core.model import Descriptor


def ingest_resolution(resolution: dict) -> tuple[list[Descriptor], list[str]]:
    """Return (new/updated descriptors, still-unresolvable ids)."""
    descriptors: list[Descriptor] = []
    unresolvable: list[str] = []
    for item in resolution.get("resolutions", []):
        if item.get("unresolvable"):
            unresolvable.append(item.get("id", "?"))
            continue
        call = item.get("boundary_call")
        if not call:
            unresolvable.append(item.get("id", "?"))
            continue
        descriptors.append(
            Descriptor(
                id=item.get("id", call),
                kind=BoundaryKind(item.get("kind", BoundaryKind.TOOL_EXEC.value)),
                match_call=call,
                output_paths=list(item.get("complete_output_fields", [])),
                emit_name=item.get("emit_name"),
            )
        )
    return descriptors, unresolvable
