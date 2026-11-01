"""Immutable acquisition capacities, independent of evidence acceptance policy.

These are operation caps, not promises that public sources will yield that many
articles. Provider/access/byte/socket limits remain enforced by native adapters.
"""
from dataclasses import asdict, dataclass, replace
from typing import Union


@dataclass(frozen=True)
class ResearchProfile:
    name: str
    max_candidates: int
    max_queries: int
    results_per_query: int
    max_reads: int
    timeout_seconds: float
    discovery_seconds: float
    read_window_seconds: float = 20.0
    concurrency: int = 4
    max_host_reads: int = 8
    host_concurrency: int = 1
    host_spacing_seconds: float = 0.15
    max_operations: int = 64
    max_wrapper_reads: int = 3
    max_discovery_reads: int = 8
    max_capture_chars: int = 400_000

    def __post_init__(self):
        # Even programmatically supplied profiles cannot open unlimited fanout.
        bounds = {
            "max_candidates": (1, 120), "max_queries": (1, 24),
            "results_per_query": (1, 12), "max_reads": (1, 25),
            "concurrency": (1, 4), "max_host_reads": (1, 8),
            "host_concurrency": (1, 2), "max_operations": (1, 80),
            "max_wrapper_reads": (0, 3), "max_discovery_reads": (0, 10),
            "max_capture_chars": (12_000, 500_000),
        }
        for name, (minimum, maximum) in bounds.items():
            value = getattr(self, name)
            if type(value) is not int or not minimum <= value <= maximum:
                raise ValueError(f"{name} must be an integer within {minimum}..{maximum}")
        if not 1 <= self.timeout_seconds <= 240:
            raise ValueError("timeout_seconds must be within 1..240")
        if not 0 < self.discovery_seconds <= self.timeout_seconds * 0.5:
            raise ValueError("discovery_seconds must reserve at least half for reading/filtering")
        if not 0 < self.read_window_seconds <= 30:
            raise ValueError("read_window_seconds must be within 0..30")
        if not 0 <= self.host_spacing_seconds <= 1:
            raise ValueError("host_spacing_seconds must be within 0..1")

    def to_dict(self):
        return asdict(self)


QUICK = ResearchProfile("QUICK", 24, 6, 5, 6, 60.0, 24.0,
                        concurrency=2, max_host_reads=3, max_operations=24,
                        max_wrapper_reads=1, max_discovery_reads=2)
STANDARD = ResearchProfile("STANDARD", 80, 16, 8, 20, 150.0, 55.0,
                           max_host_reads=6, max_operations=64,
                           max_wrapper_reads=2, max_discovery_reads=6)
DEEP = ResearchProfile("DEEP", 100, 18, 10, 24, 240.0, 90.0,
                      max_operations=80)
PROFILES = {profile.name: profile for profile in (QUICK, STANDARD, DEEP)}


def get_research_profile(value: Union[str, ResearchProfile] = "STANDARD", *,
                         timeout_seconds=None, max_reads=None):
    """Resolve a named mode; request overrides may only reduce its hard caps."""
    profile = value if isinstance(value, ResearchProfile) else PROFILES.get(str(value).upper())
    if profile is None:
        raise ValueError("Unknown research profile; choose QUICK, STANDARD or DEEP")
    changes = {}
    if timeout_seconds is not None:
        timeout = min(profile.timeout_seconds, max(1.0, float(timeout_seconds)))
        changes.update(timeout_seconds=timeout,
                       discovery_seconds=min(profile.discovery_seconds, timeout * 0.45))
    if max_reads is not None:
        changes["max_reads"] = min(profile.max_reads, max(1, int(max_reads)))
    return replace(profile, **changes) if changes else profile
