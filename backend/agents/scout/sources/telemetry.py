"""
Aegis Protocol — Scout Source Engine Telemetry
==============================================
Records detailed observability metrics, latency breakdowns, network requests,
bytes retrieved, cache hit rates, and hard gate rejection statistics.
"""

import time
from typing import Any, Dict, List


class ScoutTelemetry:
    """
    Session and request metrics tracker for Scout acquisitions.
    """

    def __init__(self):
        self.reset()

    def reset(self) -> None:
        self.start_time = time.time()
        self.discovery_latency_ms = 0
        self.acquisition_latency_ms = 0
        self.extraction_latency_ms = 0
        self.total_latency_ms = 0

        self.candidates_discovered = 0
        self.candidates_accepted_gates = 0
        self.candidates_rejected_gates = 0
        self.acquisitions_attempted = 0
        self.acquisitions_successful = 0
        self.acquisitions_failed = 0

        self.network_requests_count = 0
        self.bytes_retrieved = 0
        self.cache_hits = 0
        self.cache_misses = 0

        self.rejections_by_reason: Dict[str, int] = {}
        self.sources_by_tier: Dict[str, int] = {}

    def record_rejection(self, reason: str) -> None:
        self.candidates_rejected_gates += 1
        self.rejections_by_reason[reason] = self.rejections_by_reason.get(reason, 0) + 1

    def to_dict(self) -> Dict[str, Any]:
        self.total_latency_ms = int((time.time() - self.start_time) * 1000)
        return {
            "total_latency_ms": self.total_latency_ms,
            "discovery_latency_ms": self.discovery_latency_ms,
            "acquisition_latency_ms": self.acquisition_latency_ms,
            "extraction_latency_ms": self.extraction_latency_ms,
            "candidates_discovered": self.candidates_discovered,
            "candidates_accepted_gates": self.candidates_accepted_gates,
            "candidates_rejected_gates": self.candidates_rejected_gates,
            "acquisitions_attempted": self.acquisitions_attempted,
            "acquisitions_successful": self.acquisitions_successful,
            "acquisitions_failed": self.acquisitions_failed,
            "network_requests_count": self.network_requests_count,
            "bytes_retrieved": self.bytes_retrieved,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "rejections_by_reason": self.rejections_by_reason,
            "sources_by_tier": self.sources_by_tier,
        }
