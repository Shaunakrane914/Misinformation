"""Synthetic scheduler comparison, NOT an HTTP or scraping throughput benchmark."""
import argparse
import asyncio
import concurrent.futures
import json
import time


def _simulated_worker(query_id, latency_s=0.05):
    time.sleep(latency_s)
    return query_id, 200


async def _simulated_async_worker(query_id, sem, latency_s=0.05):
    async with sem:
        await asyncio.sleep(latency_s)
    return query_id, 200


def benchmark_threadpool(num_requests=100, max_workers=8):
    started = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as pool:
        list(pool.map(_simulated_worker, range(num_requests)))
    return time.perf_counter() - started


async def benchmark_async_engine(num_requests=100, concurrency=8):
    started = time.perf_counter()
    sem = asyncio.Semaphore(concurrency)
    await asyncio.gather(*(_simulated_async_worker(index, sem) for index in range(num_requests)))
    return time.perf_counter() - started


def run_benchmark(num_requests=100, concurrency=8):
    sync = benchmark_threadpool(num_requests, concurrency)
    asynchronous = asyncio.run(benchmark_async_engine(num_requests, concurrency))
    result = {"mode": "SYNTHETIC_SLEEP_SCHEDULER_ONLY", "real_http_requests": 0,
              "same_concurrency": concurrency, "tasks": num_requests,
              "thread_seconds": sync, "async_seconds": asynchronous,
              "observed_scheduler_ratio": sync / asynchronous,
              "acquisition_throughput": "NOT_MEASURED", "twentyfold_acceptance": "NOT_DEMONSTRATED"}
    print(json.dumps(result))
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--num-requests", type=int, default=100)
    parser.add_argument("--concurrency", type=int, default=8)
    args = parser.parse_args()
    if not 1 <= args.num_requests <= 1000 or not 1 <= args.concurrency <= 16:
        parser.error("Use 1..1000 tasks and 1..16 equal workers")
    run_benchmark(args.num_requests, args.concurrency)
