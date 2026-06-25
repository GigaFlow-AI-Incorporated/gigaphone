"""`gigaphone detect` — Phase B localization (DESIGN §8.2).

Route each confirmed descriptor to the file its ``match.call`` targets, run the language
pack's ``analyze`` there, and collect the located boundaries with their failure modes.
"""

from __future__ import annotations

from gigaphone.core.model import Boundary, Descriptor
from gigaphone.engine import project
from gigaphone.packs.registry import pack_for_path


def detect(root: str, descriptors: list[Descriptor], scope: str | None = None) -> list[Boundary]:
    boundaries: list[Boundary] = []
    files = project.scan(root, scope)
    for sf in files:
        pack = pack_for_path(sf.abs_path)
        if pack is None:
            continue
        source = project.read(sf)
        # the pack does the authoritative per-file module match inside analyze().
        boundaries.extend(pack.analyze(sf.rel_path, source, descriptors))
    return boundaries
