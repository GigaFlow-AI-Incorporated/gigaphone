"""Project scanning — locate source files under an (optional) scope, language-neutrally."""

from __future__ import annotations

import os
from dataclasses import dataclass

from gigaphone.packs.registry import all_packs, pack_for_path

_SKIP_DIRS = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    "node_modules",
    ".ruff_cache",
    ".pytest_cache",
}
_EXTS = tuple(ext for p in all_packs() for ext in p.extensions)


@dataclass
class SourceFile:
    rel_path: str  # path relative to the project root (drives module naming)
    abs_path: str


def scan(root: str, scope: str | None = None) -> list[SourceFile]:
    """All known-language source files under ``scope`` (default whole repo)."""
    base = os.path.join(root, scope) if scope else root
    base = os.path.normpath(base)
    out: list[SourceFile] = []
    if os.path.isfile(base):
        candidates = [base]
    else:
        candidates = []
        for dirpath, dirs, files in os.walk(base):
            dirs[:] = [d for d in dirs if d not in _SKIP_DIRS]
            for f in files:
                candidates.append(os.path.join(dirpath, f))
    for abs_path in sorted(candidates):
        if abs_path.endswith(_EXTS) and pack_for_path(abs_path) is not None:
            out.append(SourceFile(rel_path=os.path.relpath(abs_path, root), abs_path=abs_path))
    return out


def read(sf: SourceFile) -> str:
    with open(sf.abs_path, encoding="utf-8") as fh:
        return fh.read()
