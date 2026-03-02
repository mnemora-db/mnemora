"""Benchmark script for the Mnemora working memory (state) API.

Sends 100 sequential POST/GET/PUT requests against the live API,
measures per-request latency, and prints p50/p95/p99/min/max/mean
statistics.  The first 5 requests per operation are excluded as warmup.

Usage::

    python3 api/tests/benchmark_state.py
"""

from __future__ import annotations

import json
import os
import statistics
import time
from typing import Any
from urllib import request as urllib_request

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

API_URL = os.environ.get("MNEMORA_API_URL", "http://localhost:3000")
API_KEY = os.environ.get("MNEMORA_API_KEY", "test-key")
NUM_REQUESTS = 100
WARMUP = 5

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _request(
    method: str,
    path: str,
    body: dict[str, Any] | None = None,
) -> tuple[int, float]:
    """Send an HTTP request and return (status_code, latency_seconds)."""
    url = f"{API_URL}{path}"
    data = json.dumps(body).encode() if body else None
    req = urllib_request.Request(url, data=data, headers=HEADERS, method=method)

    start = time.perf_counter()
    try:
        with urllib_request.urlopen(req) as resp:
            resp.read()
            status = resp.status
    except Exception as exc:
        # urllib raises on 4xx/5xx — extract status from the exception
        status = getattr(exc, "code", 0)
    elapsed = time.perf_counter() - start
    return status, elapsed


def _quantile(data: list[float], q: float) -> float:
    """Return the q-th quantile (0–1) of a sorted list."""
    n = len(data)
    idx = q * (n - 1)
    lo = int(idx)
    hi = min(lo + 1, n - 1)
    frac = idx - lo
    return data[lo] * (1 - frac) + data[hi] * frac


def _print_stats(label: str, latencies: list[float], statuses: list[int]) -> None:
    """Print a stats row for one operation type."""
    # Strip warmup
    lat = sorted(latencies[WARMUP:])
    codes = statuses[WARMUP:]

    ok = sum(1 for c in codes if 200 <= c < 300)
    total = len(codes)

    p50 = _quantile(lat, 0.50)
    p95 = _quantile(lat, 0.95)
    p99 = _quantile(lat, 0.99)
    mn = min(lat)
    mx = max(lat)
    avg = statistics.mean(lat)

    print(
        f"│ {label:<8} │ {ok:>3}/{total:<3} │ "
        f"{mn * 1000:>7.1f} │ {p50 * 1000:>7.1f} │ {avg * 1000:>7.1f} │ "
        f"{p95 * 1000:>7.1f} │ {p99 * 1000:>7.1f} │ {mx * 1000:>7.1f} │"
    )


# ---------------------------------------------------------------------------
# Benchmark
# ---------------------------------------------------------------------------


def main() -> None:
    print(f"\nMnemora State API Benchmark  ({NUM_REQUESTS} requests, warmup={WARMUP})")
    print(f"Endpoint: {API_URL}")
    print()

    post_lat: list[float] = []
    post_status: list[int] = []
    get_lat: list[float] = []
    get_status: list[int] = []
    put_lat: list[float] = []
    put_status: list[int] = []

    agent_ids = [f"bench-agent-{i:04d}" for i in range(NUM_REQUESTS)]

    # ---- POST (create) ---------------------------------------------------
    print(f"Running {NUM_REQUESTS} POST requests ...", end="", flush=True)
    for i, aid in enumerate(agent_ids):
        status, elapsed = _request(
            "POST",
            "/v1/state",
            body={
                "agent_id": aid,
                "session_id": "bench-sess",
                "data": {"i": i, "value": 3.14},
                "ttl_hours": 1,
            },
        )
        post_lat.append(elapsed)
        post_status.append(status)
        if (i + 1) % 25 == 0:
            print(f" {i + 1}", end="", flush=True)
    print(" ✓")

    # ---- GET (retrieve) --------------------------------------------------
    print(f"Running {NUM_REQUESTS} GET  requests ...", end="", flush=True)
    for i, aid in enumerate(agent_ids):
        status, elapsed = _request(
            "GET",
            f"/v1/state/{aid}?session_id=bench-sess",
        )
        get_lat.append(elapsed)
        get_status.append(status)
        if (i + 1) % 25 == 0:
            print(f" {i + 1}", end="", flush=True)
    print(" ✓")

    # ---- PUT (update) ----------------------------------------------------
    print(f"Running {NUM_REQUESTS} PUT  requests ...", end="", flush=True)
    for i, aid in enumerate(agent_ids):
        status, elapsed = _request(
            "PUT",
            f"/v1/state/{aid}",
            body={
                "session_id": "bench-sess",
                "data": {"i": i, "value": 6.28, "updated": True},
                "version": 1,
            },
        )
        put_lat.append(elapsed)
        put_status.append(status)
        if (i + 1) % 25 == 0:
            print(f" {i + 1}", end="", flush=True)
    print(" ✓")

    # ---- Results ---------------------------------------------------------
    print()
    print(
        "┌──────────┬─────────┬─────────┬─────────┬─────────┬─────────┬─────────┬─────────┐"
    )
    print(
        "│ Op       │  OK/Tot │  Min ms │  p50 ms │ Mean ms │  p95 ms │  p99 ms │  Max ms │"
    )
    print(
        "├──────────┼─────────┼─────────┼─────────┼─────────┼─────────┼─────────┼─────────┤"
    )
    _print_stats("POST", post_lat, post_status)
    _print_stats("GET", get_lat, get_status)
    _print_stats("PUT", put_lat, put_status)
    print(
        "└──────────┴─────────┴─────────┴─────────┴─────────┴─────────┴─────────┴─────────┘"
    )

    # ---- Cleanup ---------------------------------------------------------
    print(f"\nCleaning up {NUM_REQUESTS} test items ...", end="", flush=True)
    for i, aid in enumerate(agent_ids):
        _request("DELETE", f"/v1/state/{aid}/bench-sess")
        if (i + 1) % 25 == 0:
            print(f" {i + 1}", end="", flush=True)
    print(" ✓  Done.\n")


if __name__ == "__main__":
    main()
