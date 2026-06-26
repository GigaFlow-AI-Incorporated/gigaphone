"""Stand-in for a third-party agent SDK — the black box. GigaPhone instruments NOTHING here
(ownership boundary: the harness author does not own this sub-agent)."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Result:
    final_output: str
    events: list = field(default_factory=list)


class Runner:
    @staticmethod
    def run(task: str) -> "Result":
        # pretend to run a whole agent (remotely); return a complete result object
        return Result(final_output=f"done: {task}", events=["plan", "act", "observe"])
