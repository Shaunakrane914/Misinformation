"""
Aegis Protocol — Unified Claim & Evidence Schemas
=================================================
Pydantic v2 validation models for claim submission, evidence citations,
structured verdicts, and API responses.
"""

from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, model_validator


class ClaimStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class VerdictType(str, Enum):
    TRUE = "True"
    FALSE = "False"
    MISLEADING = "Misleading"
    PARTIALLY_TRUE = "Partially True"
    UNVERIFIED = "Unverified"
    INSUFFICIENT_EVIDENCE = "Insufficient Evidence"


class SeverityLevel(str, Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"


class EvidenceStance(str, Enum):
    SUPPORTING = "supporting"
    REFUTING = "refuting"
    NEUTRAL = "neutral"


class EvidenceItem(BaseModel):
    """Traceable, source-grounded evidence citation item."""
    id: Optional[str] = None
    source_url: Optional[str] = None
    canonical_url: Optional[str] = None
    publisher: Optional[str] = "Primary Wire"
    title: Optional[str] = None
    author: Optional[str] = None
    published_at: Optional[str] = None
    retrieved_at: Optional[str] = None
    stance: str = "supporting"  # "supporting", "refuting", "neutral"
    summary: str
    snippet: Optional[str] = None
    credibility_score: float = Field(0.8, ge=0.0, le=1.0)
    retrieval_method: str = "agent_reach"
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SubmitClaimRequest(BaseModel):
    """Request model for submitting a claim for multi-agent verification."""
    claim_text: Optional[str] = Field(
        None,
        max_length=5000,
        description="The statement or text passage to be verified."
    )
    claim: Optional[str] = Field(
        None,
        max_length=5000,
        description="Alias for claim_text."
    )
    source_url: Optional[str] = Field(
        None,
        max_length=2048,
        description="Optional source webpage where the claim was encountered."
    )

    @model_validator(mode="before")
    @classmethod
    def resolve_claim_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            text = data.get("claim_text") or data.get("claim")
            if not text or not str(text).strip() or len(str(text).strip()) < 5:
                raise ValueError("A valid claim or claim_text of at least 5 characters is required.")
            data["claim_text"] = str(text).strip()
        return data


class SubmitClaimResponse(BaseModel):
    """Response model after initial claim ingestion."""
    claim_id: str
    status: str
    claim_hash: Optional[str] = None
    is_new: bool = True
    message: Optional[str] = None


class ClaimResult(BaseModel):
    """
    Complete result model for a claim, including source-grounded evidence citations
    and structured verdict synthesis.
    """
    claim_id: str
    claim_text: str
    normalized_text: Optional[str] = None
    status: str
    verdict: Optional[str] = None
    confidence: Optional[float] = None
    severity: Optional[str] = None
    reasoning: Optional[str] = None
    explanation: Optional[str] = None
    supporting_evidence: List[EvidenceItem] = Field(default_factory=list)
    refuting_evidence: List[EvidenceItem] = Field(default_factory=list)
    source_citations: List[str] = Field(default_factory=list)
    evidence_limitations: List[str] = Field(default_factory=list)
    evidence: Optional[Dict[str, Any]] = None  # Preserved for backward compatibility
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    verification_timestamp: Optional[str] = None
    model_metadata: Dict[str, Any] = Field(default_factory=dict)
