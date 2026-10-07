"""
Aegis Protocol — Base Platform Adapter Contract
================================================
Defines the standard interface for platform-specific acquisition and normalization
in the unified acquisition fabric. All adapters normalize into canonical FetchedDocument
and EvidenceFragment models.
"""

from abc import ABC, abstractmethod
from typing import List, Optional
from backend.services.agent_reach.channels import (
    CandidateSource,
    EvidenceFragment,
    FetchedDocument,
    RetrievalRequest,
)


class PlatformAdapter(ABC):
    """
    Abstract base adapter for platform-specific evidence acquisition.
    """

    @property
    @abstractmethod
    def platform(self) -> str:
        """Canonical platform identifier (e.g. 'web', 'reddit', 'twitter', 'youtube')."""

    @property
    @abstractmethod
    def backend_id(self) -> str:
        """Identifier of the underlying technology/mirror (e.g. 'scrapling', 'arctic_shift')."""

    @abstractmethod
    def can_handle(self, candidate: CandidateSource) -> bool:
        """Determine whether this adapter can acquire the given candidate source."""

    @abstractmethod
    def acquire(self, candidate: CandidateSource, request: RetrievalRequest) -> FetchedDocument:
        """
        Execute acquisition of raw document from the platform.
        Enforces SSRF validation, rate limiting, and timeout boundaries.
        """

    @abstractmethod
    def normalize(
        self,
        document: FetchedDocument,
        candidate: CandidateSource,
        request: RetrievalRequest,
    ) -> List[EvidenceFragment]:
        """
        Normalize fetched document into canonical EvidenceFragment records.
        Preserves honest provenance, retrieval mode, and lineage.
        """
