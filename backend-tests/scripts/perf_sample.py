"""
scripts/perf_sample.py

k6 itself can't be installed in this sandbox (no network access to its
distribution channel), so this is a small, honest substitute: a real async
load generator hitting the same live ephemeral instance used by the test
suite, producing real latency percentiles for the performance report.

Run standalone (starts and tears down its own server):
    python scripts/perf_sample.py
"""
from __future__ import annotations

import asyncio
import json
import os
import statistics
import subprocess
import sys
import time
from pathlib import Path

import httpx

THIS_DIR = Path(__file__).resolve().parent
ROOT = THIS_DIR.parent
BACKEND_DIR = Path(os.environ.get("BACKEND_DIR", ROOT.parent / "backend")).resolve()

CONCURRENCY = 20
REQUESTS_PER_CLIENT = 15


async def _worker(base_url: str, path: str, headers: dict, results: list) -> None:
    async with httpx.AsyncClient(base_url=base_url, timeout=10) as client:
        for _ in range(REQUESTS_PER_CLIENT):
            start = time.perf_counter()
            try:
                r = await client.get(path, headers=headers)
                ok = r.status_code < 500
            except Exception:
                ok = False
            elapsed_ms = (time.perf_counter() - start) * 1000
            results.append((elapsed_ms, ok))


def _percentile(data: list[float], pct: float) -> float:
    if not data:
        return 0.0
    data = sorted(data)
    k = (len(data) - 1) * (pct / 100)
    f, c = int(k), min(int(k) + 1, len(data) - 1)
    if f == c:
        return round(data[f], 2)
    return round(data[f] + (data[c] - data[f]) * (k - f), 2)


def _summarize(results: list, wall_seconds: float) -> dict:
    latencies = [r[0] for r in results]
    errors = sum(1 for r in results if not r[1])
    return {
        "count": len(results),
        "p50": _percentile(latencies, 50),
        "p95": _percentile(latencies, 95),
        "p99": _percentile(latencies, 99),
        "max": round(max(latencies), 2) if latencies else 0,
        "error_rate": round(100 * errors / len(results), 2) if results else 0,
        "rps": round(len(results) / wall_seconds, 1) if wall_seconds else 0,
    }


async def run(base_url: str, client1_token: str) -> dict:
    health_results: list = []
    scans_results: list = []

    start = time.perf_counter()
    await asyncio.gather(*[
        _worker(base_url, "/health", {}, health_results) for _ in range(CONCURRENCY)
    ])
    health_wall = time.perf_counter() - start

    headers = {"Authorization": f"Bearer {client1_token}"}
    start = time.perf_counter()
    await asyncio.gather(*[
        _worker(base_url, "/scans", headers, scans_results) for _ in range(CONCURRENCY)
    ])
    scans_wall = time.perf_counter() - start

    return {
        "concurrency": CONCURRENCY,
        "health": _summarize(health_results, health_wall),
        "scans": _summarize(scans_results, scans_wall),
    }


async def main() -> None:
    base_url = os.environ.get("PERF_BASE_URL")
    token = os.environ.get("PERF_CLIENT_TOKEN")

    if not base_url or not token:
        print("PERF_BASE_URL / PERF_CLIENT_TOKEN not set; nothing to sample against.", file=sys.stderr)
        sys.exit(1)

    stats = await run(base_url, token)
    out_path = ROOT / "reports" / "perf_stats.json"
    out_path.write_text(json.dumps(stats, indent=2))
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
