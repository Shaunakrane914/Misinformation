"""
Aegis Protocol — Personal Watch Domain Agent Package
====================================================
Autonomous personal identity protection, executive monitoring, and threat intelligence.
Owns domain entity resolution, threat-specific query planning, domain evidence extraction,
impersonation screening, threat synthesis, dossiers, and change detection.
"""

from backend.agents.personal_watch.agent import (
    PersonalAgent,
    PersonalWatchAgent,
    personal_watch_agent,
    process_personal_watch,
)
from backend.agents.personal_watch.assessment import (
    heuristic_threat_synthesis,
    synthesize_personal_threats,
)
from backend.agents.personal_watch.dossier import (
    build_investigation_dossiers,
    build_threat_timeline,
    compute_change_detection,
)
from backend.agents.personal_watch.extraction import (
    PersonalWatchExtractionEngine,
    personal_watch_extractor,
)
from backend.agents.personal_watch.identity import resolve_personal_entity
from backend.agents.personal_watch.models import (
    KNOWN_PUBLIC_PROFILES,
    SENSITIVE_PII_KEYWORDS,
    THREAT_TAXONOMY,
    CareerEvent,
    PersonalWatchExtractionResult,
    PublicStatement,
)
from backend.agents.personal_watch.monitoring import (
    analyze_spread_and_velocity,
    deduplicate_and_group_evidence,
    extract_domain,
    normalize_item,
    search_personal_evidence,
)

__all__ = [
    "PersonalWatchAgent",
    "PersonalAgent",
    "personal_watch_agent",
    "process_personal_watch",
    "THREAT_TAXONOMY",
    "KNOWN_PUBLIC_PROFILES",
    "SENSITIVE_PII_KEYWORDS",
    "CareerEvent",
    "PublicStatement",
    "PersonalWatchExtractionResult",
    "PersonalWatchExtractionEngine",
    "personal_watch_extractor",
    "resolve_personal_entity",
    "search_personal_evidence",
    "normalize_item",
    "extract_domain",
    "deduplicate_and_group_evidence",
    "analyze_spread_and_velocity",
    "synthesize_personal_threats",
    "heuristic_threat_synthesis",
    "build_investigation_dossiers",
    "build_threat_timeline",
    "compute_change_detection",
]
