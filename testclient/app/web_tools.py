"""Two more tool boundaries exhibiting the other failure modes.

- `web_search`  : already traced, but logs only a truncated repr -> `lossy_output`.
- `fetch_url`   : traced *inside a thread-pool worker* -> `off_context` (orphan trace).
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from app.tracing import tracer

_pool = ThreadPoolExecutor(max_workers=4)


def web_search(query: str) -> dict:
    """Tool boundary (kind=tool_exec). Traced, but the span records a truncated string
    while the complete `results` object is available — `lossy_output`."""
    results = {
        "query": query,
        "results": [
            {"title": "Built-in Functions — sum", "url": "https://docs.python.org/3/library/functions.html#sum"},
            {"title": "Itertools recipes", "url": "https://docs.python.org/3/library/itertools.html"},
        ],
    }
    with tracer().start_as_current_span("web_search") as span:
        span.set_attribute("tool.name", "web_search")
        span.set_attribute("tool.output", str(results)[:60])  # lossy: truncated repr
    return results


def fetch_url(url: str) -> str:
    """Tool boundary (kind=tool_exec). The work is offloaded to a worker thread that
    creates its own span — which orphans, because a plain ThreadPoolExecutor does not
    carry the agent's context across the hop — `off_context`."""
    future = _pool.submit(_fetch_blocking, url)
    return future.result()


def _fetch_blocking(url: str) -> str:
    with tracer().start_as_current_span("fetch_url") as span:
        span.set_attribute("tool.name", "fetch_url")
        body = f"<html><body>reference for {url}</body></html>"
        span.set_attribute("tool.output", body)
        return body
