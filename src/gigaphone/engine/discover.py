"""`gigaphone discover` — Phase A (DESIGN §8.2/§8.3).

Deterministic heuristic discovery: run each language pack's ``discover`` over the scoped
files and union the proposed descriptors. This is the head-less fallback the e2e uses; the
harness-driven discovery protocol (SKILL.md) can supersede or confirm these with the user
before they are committed to ``gigaphone.boundaries.yaml`` (ADR-0004, ADR-0006).
"""

from __future__ import annotations

from gigaphone.core.model import Descriptor
from gigaphone.engine import project
from gigaphone.packs.registry import pack_for_path


def discover(root: str, scope: str | None = None) -> list[Descriptor]:
    found: dict[str, Descriptor] = {}
    for sf in project.scan(root, scope):
        pack = pack_for_path(sf.abs_path)
        if pack is None:
            continue
        for d in pack.discover(sf.rel_path, project.read(sf)):
            found.setdefault(d.match_call, d)
    # stable order: gateways first, then tools, by id
    return sorted(found.values(), key=lambda d: (d.kind.value, d.id))
