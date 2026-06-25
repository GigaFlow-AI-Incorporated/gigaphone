"""Representative path GigaPhone runs during `verify` (DESIGN §12).

Exercises every tool boundary once so the backend adapter can confirm each tool span is
present, nested under the agent trace, and complete.
"""
from __future__ import annotations

from app.agent import run_agent
from app.tracing import init_tracing


def main() -> str:
    init_tracing()
    answer = run_agent("Compute the sum of 0..9 and find a reference for Python's sum().")
    print(answer)
    return answer


if __name__ == "__main__":
    main()
