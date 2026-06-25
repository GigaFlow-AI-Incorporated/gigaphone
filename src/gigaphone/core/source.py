"""Source byte-offset mapping for byte-accurate, reformat-free codemods (golden principle 7).

`ast` reports 1-based line / 0-based character column; codemods need UTF-8 byte offsets.
``SourceMap`` converts between them.
"""

from __future__ import annotations


class SourceMap:
    def __init__(self, source: str) -> None:
        self.source = source
        # byte offset of the start of each 1-based line
        self._line_start: list[int] = [0]
        b = 0
        for line in source.splitlines(keepends=True):
            b += len(line.encode("utf-8"))
            self._line_start.append(b)

    def offset(self, line: int, col: int) -> int:
        """Byte offset of (1-based line, 0-based character column)."""
        base = self._line_start[line - 1]
        # advance `col` characters into the line, counting their UTF-8 byte width
        line_text = (
            self.source.splitlines(keepends=True)[line - 1]
            if line - 1 < len(self.source.splitlines(keepends=True))
            else ""
        )
        return base + len(line_text[:col].encode("utf-8"))

    def line_start_offset(self, line: int) -> int:
        return self._line_start[line - 1]
