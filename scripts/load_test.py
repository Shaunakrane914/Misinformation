"""
Aegis Protocol — Asynchronous High-Concurrency Load Testing Benchmark
=======================================================================
Benchmarks FastAPI backend throughput (RPS) and latency percentiles (p50, p95, p99)
using non-blocking httpx.AsyncClient across concurrent worker coroutines.

Usage:
    python scripts/load_test.py --concurrency 10 --requests 50 --endpoint /api/healthz
"""

import sys
import time
import asyncio
import argparse
import os
import sys
import statistics
from typing import List, Dict, Any, Optional
import httpx
from httpx import ASGITransport

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


async def run_worker(
    worker_id: int,
    url: str,
    method: str,
    payload: Dict[str, Any],
    num_requests: int,
    latencies: List[float],
    status_codes: Dict[int, int],
    transport: Optional[Any] = None
):
    client_kwargs: Dict[str, Any] = {"timeout": 15.0}
    if transport:
        client_kwargs["transport"] = transport

    async with httpx.AsyncClient(**client_kwargs) as client:
        for _ in range(num_requests):
            t0 = time.perf_counter()
            try:
                if method.upper() == "POST":
                    resp = await client.post(url, json=payload)
                else:
                    resp = await client.get(url)
                duration_ms = (time.perf_counter() - t0) * 1000.0
                latencies.append(duration_ms)
                status_codes[resp.status_code] = status_codes.get(resp.status_code, 0) + 1
            except Exception as e:
                duration_ms = (time.perf_counter() - t0) * 1000.0
                latencies.append(duration_ms)
                status_codes[599] = status_codes.get(599, 0) + 1


async def main():
    parser = argparse.ArgumentParser(description="Aegis Protocol Concurrency Benchmark")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="Target server base URL")
    parser.add_argument("--endpoint", default="/api/healthz", help="Endpoint path to benchmark")
    parser.add_argument("--method", default="GET", choices=["GET", "POST"], help="HTTP Method")
    parser.add_argument("--concurrency", type=int, default=10, help="Number of concurrent worker coroutines")
    parser.add_argument("--requests", type=int, default=50, help="Total requests across all workers")
    parser.add_argument("--in-process", action="store_true", help="Benchmark in-process ASGI app without external server")
    args = parser.parse_args()

    transport = None
    if args.in_process:
        from backend.main import app
        transport = ASGITransport(app=app)
        base = "http://test"
    else:
        base = args.base_url.rstrip('/')

    url = f"{base}{args.endpoint}"
    reqs_per_worker = max(1, args.requests // args.concurrency)
    actual_total = reqs_per_worker * args.concurrency

    sample_payload = {}
    if args.method == "POST":
        if "synthetic" in args.endpoint:
            sample_payload = {"text": "Distributed algorithmic consensus achieves Byzantine fault tolerance under partial network synchrony."}
        elif "consensus" in args.endpoint:
            sample_payload = {"claim": "Scientists confirm the Earth orbits the Sun in an elliptical path."}
        else:
            sample_payload = {"claim": "Warm lemon water cures all diabetes within 2 weeks."}

    print("=" * 70)
    print(f"AEGIS PROTOCOL LOAD BENCHMARK: {args.method} {url}")
    print(f"Concurrency: {args.concurrency} workers | Total Requests: {actual_total}")
    print("=" * 70)

    latencies: List[float] = []
    status_codes: Dict[int, int] = {}

    start_wall = time.perf_counter()
    tasks = [
        run_worker(i, url, args.method, sample_payload, reqs_per_worker, latencies, status_codes, transport=transport)
        for i in range(args.concurrency)
    ]
    await asyncio.gather(*tasks)
    total_time = time.perf_counter() - start_wall

    rps = len(latencies) / total_time if total_time > 0 else 0
    latencies.sort()

    p50 = statistics.median(latencies) if latencies else 0
    p95 = latencies[int(len(latencies) * 0.95)] if latencies else 0
    p99 = latencies[int(len(latencies) * 0.99)] if latencies else 0
    mean_lat = statistics.mean(latencies) if latencies else 0

    print("\nBENCHMARK RESULTS:")
    print(f"  Total Duration:     {total_time:.2f} s")
    print(f"  Throughput:         {rps:.1f} req/s")
    print(f"  Latency (Mean):     {mean_lat:.2f} ms")
    print(f"  Latency (p50):      {p50:.2f} ms")
    print(f"  Latency (p95):      {p95:.2f} ms")
    print(f"  Latency (p99):      {p99:.2f} ms")
    print(f"  Status Codes:       {status_codes}")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
