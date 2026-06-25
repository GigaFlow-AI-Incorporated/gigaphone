"""Code-execution tool — the headline failure: an UNTRACED consumption boundary.

`run_code` collects the complete execution result on the agent thread (the in-process
consumption boundary, DESIGN §3) and hands it back to the loop. Before GigaPhone it has
no span, so the complete stdout/stderr/exit_code never reach the trace — the only record
is the truncated string the model sees. GigaPhone traces this boundary and records the
complete result.
"""
from __future__ import annotations

import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

_pool = ThreadPoolExecutor(max_workers=4)


@dataclass
class ExecResult:
    stdout: str
    stderr: str
    exit_code: int


def run_code(code: str) -> ExecResult:
    """Tool boundary (kind=tool_exec). Returns the COMPLETE result.

    Treats the sandbox (here a subprocess) as a black box and instruments nothing inside
    it; the result is consumed here, on the agent's call stack.
    """
    future = _pool.submit(_exec, code)
    return future.result()


def _exec(code: str) -> ExecResult:
    proc = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, timeout=10
    )
    return ExecResult(stdout=proc.stdout, stderr=proc.stderr, exit_code=proc.returncode)
