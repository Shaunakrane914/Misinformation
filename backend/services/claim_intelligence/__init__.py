"""Claim Intelligence Core.

Shared narrative intelligence foundation powering Scout, BrandShield, Trending,
and Personal Watch agents with atomic claim decomposition, provenance grounding,
Source Independence Graph, and the Allegation vs. Evidence Matrix.
"""
from __future__ import annotations

from backend.services.claim_intelligence.models import (
    AllegationMatrixItem,
    AtomicClaim,
    CorroborationGroup,
    CorroborationSummary,
    DeceptiveFramingType,
    EpistemicOutcome,
    EvidenceLink,
    MisinformationDossier,
    NarrativeVersion,
    SourceCapture,
    SourceRelationship,
    SourceRelationType,
    StanceType,
)
from backend.services.claim_intelligence.claim_extractor import (
    ClaimExtractor,
    claim_extractor,
)
from backend.services.claim_intelligence.stance_analysis import (
    StanceAnalyzer,
    stance_analyzer,
)
from backend.services.claim_intelligence.corroboration import (
    CorroborationDetector,
    corroboration_detector,
)
from backend.services.claim_intelligence.assessment import (
    AllegationAssessmentEngine,
    assessment_engine,
)

__all__ = [
    "AllegationMatrixItem",
    "AtomicClaim",
    "CorroborationGroup",
    "CorroborationSummary",
    "DeceptiveFramingType",
    "EpistemicOutcome",
    "EvidenceLink",
    "MisinformationDossier",
    "NarrativeVersion",
    "SourceCapture",
    "SourceRelationship",
    "SourceRelationType",
    "StanceType",
    "ClaimExtractor",
    "claim_extractor",
    "StanceAnalyzer",
    "stance_analyzer",
    "CorroborationDetector",
    "corroboration_detector",
    "AllegationAssessmentEngine",
    "assessment_engine",
]

