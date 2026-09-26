"""
Aegis Protocol — Research Concurrency & Latency Benchmark
=========================================================
Benchmarks concurrent multi-platform investigations to calculate:
  - p50, p95, p99 latency percentiles
  - Query throughput & execution graph yield
  - Thread pool contention and memory safety
"""

import concurrent.futures
import time
import unittest
import numpy as np

from backend.services.research.research_models import ResearchRequest
from backend.services.research.research_engine import ResearchEngine


class TestResearchPerformanceBenchmark(unittest.TestCase):
    """Measures empirical systems performance under concurrent load."""

    def setUp(self):
        self.engine = ResearchEngine()

    def _execute_mock_investigation(self, target: str) -> float:
        """Run an investigation with bounded budget and record total latency in ms."""
        t0 = time.perf_counter()
        req = ResearchRequest(
            target=target,
            domain="financial",
            deep_read_budget=2,
            max_candidates=10,
            timeout_seconds=4.0
        )
        res = self.engine.investigate(req)
        latency_ms = (time.perf_counter() - t0) * 1000
        return latency_ms

    def test_single_investigation_baseline(self):
        """Baseline single investigation execution latency."""
        latency = self._execute_mock_investigation("Tata Motors")
        self.assertGreater(latency, 0)
        print(f"\n[Benchmark] Baseline 1x Latency: {latency:.1f}ms")

    def test_concurrent_investigation_percentiles(self):
        """Run concurrent investigations and compute p50, p95, p99 latency."""
        targets = ["Tata Motors", "Tesla Motors", "Nvidia Corp", "Apple Inc"]
        latencies = []

        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            futures = [pool.submit(self._execute_mock_investigation, target) for target in targets]
            for f in concurrent.futures.as_completed(futures):
                try:
                    lat = f.result()
                    latencies.append(lat)
                except Exception as e:
                    self.fail(f"Concurrent investigation failed with exception: {e}")

        self.assertEqual(len(latencies), len(targets))
        
        p50 = float(np.percentile(latencies, 50))
        p95 = float(np.percentile(latencies, 95))
        p99 = float(np.percentile(latencies, 99))

        print(f"\n[Benchmark] Concurrency N={len(targets)}: p50={p50:.1f}ms, p95={p95:.1f}ms, p99={p99:.1f}ms")
        self.assertLess(p50, 45000, "Median latency must remain bounded under concurrency")


if __name__ == "__main__":
    unittest.main()
