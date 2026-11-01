"""Domain models for Claim Intelligence Core.

Follows W3C PROV-O provenance ontology (Entity, Activity, Agent, Derivation)
and epistemic truth qualification contracts. All models use Pydantic V2.
"""
from __future__ import annotations

import hashlib
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field


class EpistemicOutcome(str, Enum):
    """Calibrated 6-state epistemic verdict."""
    SUPPORTED = "SUPPORTED"
    REFUTED = "REFUTED"
    MISLEADING_CONTEXT = "MISLEADING_CONTEXT"
    MIXED = "MIXED"
    UNVERIFIED = "UNVERIFIED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class StanceType(str, Enum):
    """Passage-level stance towards an atomic proposition."""
    SUPPORTS = "SUPPORTS"
    CONTRADICTS = "CONTRADICTS"
    MENTIONS = "MENTIONS"
    IRRELEVANT = "IRRELEVANT"


class SourceRelationType(str, Enum):
    """Provenance relationship between two sources."""
    ORIGINAL_REPORTING = "ORIGINAL_REPORTING"
    EXPLICIT_REPRINT = "EXPLICIT_REPRINT"
    QUOTES = "QUOTES"
    HIGH_TEXT_SIMILARITY = "HIGH_TEXT_SIMILARITY"
    INDEPENDENT_REPORTING = "INDEPENDENT_REPORTING"
    UNKNOWN_RELATIONSHIP = "UNKNOWN_RELATIONSHIP"


class DeceptiveFramingType(str, Enum):
    """Specific manipulation tactics and misleading framing patterns."""
    OUT_OF_CONTEXT_MEDIA = "OUT_OF_CONTEXT_MEDIA"
    QUOTE_CLIPPING = "QUOTE_CLIPPING"
    FABRICATED_AUTHORITY = "FABRICATED_AUTHORITY"
    CORROBORATION_ILLUSION = "CORROBORATION_ILLUSION"
    CORRELATION_FALLACY = "CORRELATION_FALLACY"
    MISATTRIBUTED_STATEMENT = "MISATTRIBUTED_STATEMENT"
    UNSUBSTANTIATED_ESCALATION = "UNSUBSTANTIATED_ESCALATION"


class AtomicClaim(BaseModel):
    """An atomic, testable claim decomposed from an investigation request."""
    claim_id: str = Field(description="Unique identifier for the atomic claim, e.g. clm_a1b2c3d4")
    raw_allegation: str = Field(description="The exact user input or circulating rumor phrasing")
    normalized_proposition: str = Field(description="Standardized, declarative proposition for testing")
    target_entity: str = Field(description="Primary entity (company, brand, individual)")
    predicate: str = Field(default="", description="Core action or state (e.g. recalled, arrested, sued)")
    subject_scope: str = Field(default="unspecified", description="Scope of subject (e.g. all products, batch #104, global)")
    temporal_scope: Optional[str] = Field(default=None, description="Explicit time window asserted (e.g. today, Q1 2024, historical)")
    extracted_qualifiers: List[str] = Field(default_factory=list, description="Preserved modifiers, negations, or uncertainty cues")
    is_negated: bool = Field(default=False, description="Whether the proposition asserts a negative (did not occur)")

    @classmethod
    def create(
        cls,
        raw_allegation: str,
        target_entity: Any,
        normalized_proposition: Optional[str] = None,
        predicate: str = "",
        subject_scope: str = "unspecified",
        temporal_scope: Optional[str] = None,
        extracted_qualifiers: Optional[List[str]] = None,
        is_negated: bool = False,
    ) -> AtomicClaim:
        if isinstance(target_entity, dict):
            t_ent = str(target_entity.get("name") or target_entity.get("brand") or target_entity.get("issuer") or "Subject").strip()
        else:
            t_ent = str(target_entity or "Subject").strip()
        norm = normalized_proposition or (raw_allegation.strip() if isinstance(raw_allegation, str) else str(raw_allegation))
        digest = hashlib.sha256(f"{t_ent}|{norm}|{temporal_scope}".encode("utf-8")).hexdigest()[:12]
        return cls(
            claim_id=f"clm_{digest}",
            raw_allegation=raw_allegation.strip() if isinstance(raw_allegation, str) else str(raw_allegation),
            normalized_proposition=norm,
            target_entity=t_ent,
            predicate=predicate.strip() if isinstance(predicate, str) else str(predicate),
            subject_scope=subject_scope.strip() if isinstance(subject_scope, str) else str(subject_scope),
            temporal_scope=temporal_scope.strip() if temporal_scope and isinstance(temporal_scope, str) else None,
            extracted_qualifiers=extracted_qualifiers or [],
            is_negated=is_negated,
        )


class SourceCapture(BaseModel):
    """Cryptographically sealed representation of an acquired source."""
    source_id: str
    canonical_url: str
    publisher: str
    publisher_domain: str
    published_at: Optional[str] = None
    captured_at: str
    content_hash: str = Field(description="SHA-256 hash of raw captured bytes/text")
    authoritative: bool = False
    source_tier: str = "SECONDARY"  # PRIMARY, FACT_CHECK, JOURNALISM, AGGREGATOR, COMMUNITY
    is_corporate_denial: bool = False  # Denials count as evidence of denial, not proof of falsity


class EvidenceLink(BaseModel):
    """Passage-level grounded link testing an atomic claim against captured text."""
    link_id: str
    claim_id: str
    source_id: str
    source_url: str
    publisher: str
    published_at: Optional[str] = None
    passage_text: str = Field(description="Exact quoted passage from source")
    passage_offsets: Tuple[int, int] = Field(description="Exact character start and end in source content")
    content_hash: str = Field(description="SHA-256 digest of passage_text ensuring byte fidelity")
    stance: StanceType
    confidence: float = Field(ge=0.0, le=1.0)
    is_corporate_denial: bool = False
    temporal_match: bool = Field(default=True, description="Whether evidence aligns with the claim's asserted time window")
    rationale: str

    @classmethod
    def create(
        cls,
        claim_id: str,
        source_id: str,
        source_url: str,
        publisher: str,
        passage_text: str,
        passage_offsets: Tuple[int, int],
        stance: StanceType,
        confidence: float,
        rationale: str,
        published_at: Optional[str] = None,
        is_corporate_denial: bool = False,
        temporal_match: bool = True,
    ) -> EvidenceLink:
        chash = hashlib.sha256(passage_text.encode("utf-8")).hexdigest()
        lid = "elk_" + hashlib.sha256(f"{claim_id}|{source_id}|{passage_offsets[0]}".encode("utf-8")).hexdigest()[:12]
        return cls(
            link_id=lid,
            claim_id=claim_id,
            source_id=source_id,
            source_url=source_url,
            publisher=publisher,
            published_at=published_at,
            passage_text=passage_text,
            passage_offsets=passage_offsets,
            content_hash=chash,
            stance=stance,
            confidence=confidence,
            is_corporate_denial=is_corporate_denial,
            temporal_match=temporal_match,
            rationale=rationale,
        )


class SourceRelationship(BaseModel):
    """Directional or bidirectional provenance edge between two publications."""
    edge_id: str
    source_a_id: str
    source_b_id: str
    relation_type: SourceRelationType
    similarity_score: float = Field(ge=0.0, le=1.0, default=0.0)
    shared_quotes: List[str] = Field(default_factory=list)
    attribution_url: Optional[str] = None
    rationale: str = ""


class NarrativeVersion(BaseModel):
    """A distinct observed phrasing or mutation step in the claim's spread."""
    version_id: str
    claim_id: str
    phrasing: str
    earliest_source_id: str
    earliest_publisher: str
    earliest_observed_at: str
    mutation_type: str = "ORIGIN"  # ORIGIN, ESCALATION, SPECULATION, AMPLIFICATION, REFUTATION
    amplification_count: int = 1


class CorroborationGroup(BaseModel):
    """Cluster of sources sharing an identical reporting origin or syndication chain."""
    group_id: str
    primary_origin_publisher: str
    primary_origin_url: str
    reprint_publishers: List[str] = Field(default_factory=list)
    all_source_ids: List[str] = Field(default_factory=list)
    is_independent: bool = True
    syndication_ratio: float = Field(default=1.0, description="Reprint count / total in group")


class CorroborationSummary(BaseModel):
    """Summary of source independence and corroboration illusion assessment."""
    total_sources_scanned: int
    unique_publishers: int
    independent_evidence_chains: int
    syndicated_reprints_count: int
    corroboration_illusion_detected: bool
    corroboration_ratio: float = Field(description="independent_chains / unique_publishers")
    warning_message: Optional[str] = None
    groups: List[CorroborationGroup] = Field(default_factory=list)


class AllegationMatrixItem(BaseModel):
    """Side-by-side deconstruction of an atomic claim vs verified public record."""
    claim: AtomicClaim
    verdict: EpistemicOutcome
    confidence: float = Field(ge=0.0, le=1.0)
    allegation_summary: str
    verified_record_summary: str
    supporting_links: List[EvidenceLink] = Field(default_factory=list)
    contradicting_links: List[EvidenceLink] = Field(default_factory=list)
    mention_links: List[EvidenceLink] = Field(default_factory=list)
    corporate_denials: List[EvidenceLink] = Field(default_factory=list)
    deceptive_framing_flags: List[DeceptiveFramingType] = Field(default_factory=list)
    registries_checked: List[str] = Field(default_factory=list)
    unresolved_uncertainty: List[str] = Field(default_factory=list)
    action_advisory: str


class MisinformationDossier(BaseModel):
    """Complete structured investigation export matching frontend & Schema.org."""
    investigation_id: str
    created_at: str
    target_entity: str
    raw_query: str
    agent: str
    overall_verdict: EpistemicOutcome
    actionability_advisory: Dict[str, Any]
    allegation_matrix: List[AllegationMatrixItem]
    corroboration_summary: CorroborationSummary
    provenance_edges: List[SourceRelationship] = Field(default_factory=list)
    narrative_mutations: List[NarrativeVersion] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)
    claim_review_schema: Optional[Dict[str, Any]] = None

