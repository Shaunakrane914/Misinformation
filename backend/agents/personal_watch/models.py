"""
Aegis Protocol — Personal Watch Domain Models & Catalogs
=========================================================
14-class threat taxonomy, known public figure profiles, privacy guard keywords,
and typed personal intelligence records.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


# ── 14-Class Threat Taxonomy ──────────────────────────────────────────────────
THREAT_TAXONOMY = {
    "IMPERSONATION": "Spoofed social profiles, lookalike accounts, or unauthorized representation.",
    "PHISHING": "Deceptive login portals, credential harvesting, or spoofed domains targeting users.",
    "SCAM": "Fraudulent giveaways, investment solicitations, fake crypto offerings, or unauthorized commercial offers.",
    "DEEPFAKE": "Public claims of AI voice cloning, fabricated audio statements, or synthetic face swaps.",
    "SYNTHETIC_MEDIA": "Manipulated video clips, out-of-context soundbites, or AI-generated imagery.",
    "FALSE_CLAIM": "Substantive unverified factual assertions regarding conduct, health, arrest, or death.",
    "DOXXING_PRIVACY": "Public disclosure or circulating dumps of private contact data, credentials, or personal files.",
    "HARASSMENT": "Coordinated harassment brigading, targeted mass abuse, or digital intimidation.",
    "REPUTATION_ATTACK": "Coordinated smear campaigns, defamatory narratives, or astroturfed outrage.",
    "FRAUDULENT_ANNOUNCEMENT": "Fabricated public statements, bogus policy announcements, or forged official releases.",
    "FAKE_GIVEAWAY": "Social media giveaway scams falsely using the subject's name and likeness.",
    "IDENTITY_MISUSE": "Unauthorized commercial exploitation of the subject's name, brand, or persona.",
    "COORDINATED_CAMPAIGN": "Multi-platform synchronized narrative propagation or inorganic burst activity.",
    "UNVERIFIED_RUMOR": "Speculative gossip circulating across community forums without primary evidence."
}

# ── Sensitive PII Keywords for Strict Privacy Guard ────────────────────────────
SENSITIVE_PII_KEYWORDS = {
    "home address", "residential address", "medical record", "health diagnosis",
    "children school", "personal bank account", "ssn", "passport number",
}

# ── Public Figure Entity Resolution Catalog ────────────────────────────────────
KNOWN_PUBLIC_PROFILES = {
    "ELON MUSK": {
        "canonical_name": "Elon Musk",
        "aliases": ["Elon", "Musk"],
        "category": "executive",
        "handles": {"twitter": "@elonmusk"},
        "domains": ["x.com", "tesla.com", "spacex.com", "x.ai"],
        "affiliations": ["Tesla", "SpaceX", "X", "xAI", "Neuralink"]
    },
    "SAM ALTMAN": {
        "canonical_name": "Sam Altman",
        "aliases": ["Sama"],
        "category": "executive",
        "handles": {"twitter": "@sama"},
        "domains": ["openai.com", "blog.samaltman.com"],
        "affiliations": ["OpenAI", "Y Combinator", "Worldcoin"]
    },
    "MR BEAST": {
        "canonical_name": "MrBeast",
        "aliases": ["Mr Beast", "Jimmy Donaldson"],
        "category": "creator",
        "handles": {"youtube": "MrBeast", "twitter": "@MrBeast", "instagram": "@mrbeast"},
        "domains": ["mrbeast.com", "beastphilanthropy.org"],
        "affiliations": ["MrBeast LLC", "Feastables"]
    },
    "MRBEAST": {
        "canonical_name": "MrBeast",
        "aliases": ["Jimmy Donaldson", "Mr Beast"],
        "category": "creator",
        "handles": {"youtube": "MrBeast", "twitter": "@MrBeast", "instagram": "@mrbeast"},
        "domains": ["mrbeast.com", "beastphilanthropy.org"],
        "affiliations": ["MrBeast LLC", "Feastables"]
    },
    "VIRAT KOHLI": {
        "canonical_name": "Virat Kohli",
        "aliases": ["King Kohli", "Kohli", "VK"],
        "category": "public_figure",
        "handles": {"twitter": "@imVkohli", "instagram": "@virat.kohli"},
        "domains": ["one8.com"],
        "affiliations": ["Indian Cricket Team", "Royal Challengers Bengaluru"]
    },
    "TAYLOR SWIFT": {
        "canonical_name": "Taylor Swift",
        "aliases": ["Swift"],
        "category": "creator",
        "handles": {"twitter": "@taylorswift13", "instagram": "@taylorswift"},
        "domains": ["taylorswift.com"],
        "affiliations": ["Taylor Swift Touring", "Republic Records"]
    },
    "NARENDRA MODI": {
        "canonical_name": "Narendra Modi",
        "aliases": ["Modi", "PM Modi"],
        "category": "public_figure",
        "handles": {"twitter": "@narendramodi", "youtube": "narendramodi"},
        "domains": ["narendramodi.in", "pmindia.gov.in"],
        "affiliations": ["Government of India", "PMO India"]
    },
    "SUNDAR PICHAI": {
        "canonical_name": "Sundar Pichai",
        "aliases": ["Pichai"],
        "category": "executive",
        "handles": {"twitter": "@sundarpichai"},
        "domains": ["google.com", "alphabet.com"],
        "affiliations": ["Google", "Alphabet"]
    },
    "SATYA NADELLA": {
        "canonical_name": "Satya Nadella",
        "aliases": ["Nadella"],
        "category": "executive",
        "handles": {"twitter": "@satyanadella"},
        "domains": ["microsoft.com"],
        "affiliations": ["Microsoft"]
    },
    "JENSEN HUANG": {
        "canonical_name": "Jensen Huang",
        "aliases": ["Jen-Hsun Huang"],
        "category": "executive",
        "handles": {},
        "domains": ["nvidia.com"],
        "affiliations": ["NVIDIA"]
    }
}


@dataclass
class CareerEvent:
    event_id: str
    person: str
    role: str
    organization: str
    event_type: str                         # "APPOINTMENT" | "RESIGNATION" | "BOARD_SEAT" | "FOUNDING"
    summary: str
    evidence_ids: List[str] = field(default_factory=list)
    confidence: float = 0.90

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "person": self.person,
            "role": self.role,
            "organization": self.organization,
            "event_type": self.event_type,
            "summary": self.summary,
            "evidence_ids": self.evidence_ids,
            "confidence": self.confidence,
        }


@dataclass
class PublicStatement:
    statement_id: str
    speaker: str
    context: str
    statement_text: str
    platform: str
    evidence_ids: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "statement_id": self.statement_id,
            "speaker": self.speaker,
            "context": self.context,
            "statement_text": self.statement_text,
            "platform": self.platform,
            "evidence_ids": self.evidence_ids,
        }


@dataclass
class PersonalWatchExtractionResult:
    target_person: str
    identity_confidence: float = 0.95
    career_events: List[CareerEvent] = field(default_factory=list)
    public_statements: List[PublicStatement] = field(default_factory=list)
    impersonation_alerts: List[Dict[str, Any]] = field(default_factory=list)
    timeline: List[Dict[str, Any]] = field(default_factory=list)
    privacy_filtered_count: int = 0
    total_signals_analyzed: int = 0
    extracted_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @property
    def threats(self) -> List[Dict[str, Any]]:
        return [
            {
                "threat_id": a.get("alert_id", "thr_01"),
                "threat_type": "IMPERSONATION",
                "risk_level": a.get("threat_level", "HIGH"),
                "title": a.get("summary", "Impersonation risk"),
                "reason": a.get("summary", "Lookalike account"),
                "platform": a.get("platform", "Web"),
                "evidence_ids": a.get("evidence_ids", []),
                "confidence": 0.85,
                "indicators": ["Lookalike account"],
            }
            for a in self.impersonation_alerts
        ]

    @property
    def impersonations(self) -> List[Dict[str, Any]]:
        return self.impersonation_alerts

    def to_dict(self) -> Dict[str, Any]:
        return {
            "target_person": self.target_person,
            "identity_confidence": self.identity_confidence,
            "career_events": [c.to_dict() for c in self.career_events],
            "public_statements": [s.to_dict() for s in self.public_statements],
            "impersonation_alerts": self.impersonation_alerts,
            "threats": self.threats,
            "impersonations": self.impersonations,
            "timeline": self.timeline,
            "privacy_filtered_count": self.privacy_filtered_count,
            "total_signals_analyzed": self.total_signals_analyzed,
            "extracted_at": self.extracted_at,
        }
