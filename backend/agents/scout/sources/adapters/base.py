"""
Aegis Protocol — Scout Source Adapter Interface
===============================================
Defines the abstract interface for platform-specific acquisition and extraction adapters.
"""

from abc import ABC, abstractmethod
from typing import Optional
from backend.agents.scout.sources.models import CandidateSource, RawSource, ScoutEvidence, ScoutSourceRequest


class ScoutSourceAdapter(ABC):
    """
    Abstract adapter for a specific source platform or tier.
    Adapters know how to:
    1. Verify if they can handle a candidate
    2. Acquire raw source data via the optimal cascade mechanism
    3. Extract structured evidence and metadata
    """

    @abstractmethod
    def can_handle(self, candidate: CandidateSource) -> bool:
        """Return True if this adapter is suitable for the candidate source."""
        pass

    @abstractmethod
    def acquire(self, candidate: CandidateSource, request: ScoutSourceRequest) -> RawSource:
        """Acquire the raw content using the cheapest reliable mechanism."""
        pass

    @abstractmethod
    def extract(self, raw: RawSource, request: ScoutSourceRequest) -> Optional[ScoutEvidence]:
        """Extract structured evidence, financial facts, and events from raw content."""
        pass
