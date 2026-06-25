"""LanguagePack interface — the *language* axis (DESIGN §7, ADR-0002, ADR-0007).

Parser-agnostic: the engine talks to this interface over the neutral core model
(``Boundary`` / ``CodeEdit``) and never sees a parser type. The Python pack uses stdlib
``ast`` (ADR-0007); other packs may use tree-sitter. Either way a pack carries everything
language-specific so the engine, classifier, specs, plan records, and both adapters stay
language-neutral. A new language is a new pack with **no engine change**.

v1 ships ``python`` (full) and ``typescript`` (catalog + emitters).
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from gigaphone.core.model import Boundary, CodeEdit, Descriptor, FixPrimitive


class LanguagePack(ABC):
    """One concrete subclass per language."""

    id: str  # "python" | "typescript" | ...
    extensions: tuple[str, ...]  # (".py",) | (".ts", ".tsx") | ...

    @abstractmethod
    def analyze(self, path: str, source: str, descriptors: list[Descriptor]) -> list[Boundary]:
        """Localization (Phase B, DESIGN §8.2): run the built-in anchor catalog plus the
        confirmed config descriptors over one source file, walk shallow def-use, and return
        the boundaries found with their detected failure modes. Byte-accurate."""

    @abstractmethod
    def discover(self, path: str, source: str) -> list[Descriptor]:
        """Deterministic heuristic discovery (Phase A fallback, DESIGN §8.3): propose
        codebase-specific boundary descriptors (gateway, tool dispatch, execution sinks)
        for one source file. The harness-driven protocol may supersede or confirm these."""

    @abstractmethod
    def emit_fix(self, boundary: Boundary, primitive: FixPrimitive, source: str) -> CodeEdit | None:
        """Render a backend fix primitive into this language's syntax as a byte-accurate,
        idempotent edit. Returns None if the boundary already carries the fix (upgrade in
        place / no double-wrapping). The ``off_context`` signatures and codemod emitters are
        localized here per the pack spec (DESIGN §7)."""
