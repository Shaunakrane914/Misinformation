"""Sampled peak memory and process CPU for a block of work (stdlib + psutil, no network).

Peak RSS is sampled, not exact: a spike shorter than the interval can be missed. CPU is the process's own
user+system time, so it includes every thread in the process but not child processes.
"""
from __future__ import annotations

import threading
import time

#: Render Free tier as stated by the project owner; used only for the labelled projection below.
RENDER_FREE_CPU_SHARE = 0.1
RENDER_FREE_RAM_MB = 512


class ResourceSampler:
    def __init__(self, interval: float = 0.05):
        self.process, self.unavailable = None, None
        try:
            import psutil
            self.process = psutil.Process()
        except Exception as error:
            self.unavailable = type(error).__name__
        self.interval, self.peak, self.threads = interval, 0, 0
        self._stop = threading.Event()

    def __enter__(self):
        self.cpu0, self.t0 = time.process_time(), time.perf_counter()
        self.thread = None
        if self.process is not None:
            try:
                self.peak = self.process.memory_info().rss
                self.thread = threading.Thread(target=self._loop, daemon=True, name="resource-sampler")
                self.thread.start()
            except Exception as error:
                self.unavailable = type(error).__name__
                self.process = None
        return self

    def _loop(self):
        while not self._stop.is_set():
            try:
                self.peak = max(self.peak, self.process.memory_info().rss)
                self.threads = max(self.threads, self.process.num_threads())
            except Exception:
                pass
            self._stop.wait(self.interval)

    def __exit__(self, *exc):
        self._stop.set()
        if self.thread is not None and self.thread.ident is not None:
            self.thread.join(timeout=1)
        self.wall = time.perf_counter() - self.t0
        self.cpu = time.process_time() - self.cpu0

    def result(self):
        cpu = round(self.cpu, 3)
        return {
            "peak_rss_mb": round(self.peak / 1_048_576, 1) if self.process is not None else None,
            "memory_measurement_status": "AVAILABLE_SAMPLED" if self.process is not None else "UNAVAILABLE",
            "memory_unavailable_reason": self.unavailable,
            "process_cpu_seconds": cpu,
            "wall_seconds_measured": round(self.wall, 3),
            "peak_threads": self.threads if self.process is not None else None,
            "cpu_fraction_of_one_core": round(self.cpu / self.wall, 3) if self.wall else None,
            "sample_interval_seconds": self.interval,
            "render_free_projection_ESTIMATE": {
                "minimum_cpu_bound_seconds": round(cpu / RENDER_FREE_CPU_SHARE, 1),
                "assumes": f"{RENDER_FREE_CPU_SHARE} CPU share; network waits add to, not replace, this floor",
                "peak_rss_within_ram_limit": self.peak / 1_048_576 <= RENDER_FREE_RAM_MB if self.process is not None else None,
            },
            "scope": "Whole Python process during the measured block (sampled); not an isolated container measurement",
        }
