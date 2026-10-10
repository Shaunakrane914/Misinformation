"""
Aegis Protocol — BrandShield Models & Catalogs
===============================================
Domain-specific threat taxonomy, entity catalog, and typed extraction records.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


# ── 12-Class Threat Taxonomy ──────────────────────────────────────────────────
THREAT_TAXONOMY = {
    "COUNTERFEIT": "Unauthorized knockoffs, replica goods, clone listings, or unauthorized sellers.",
    "FAKE_REVIEW": "Coordinated review brigades, astroturfing, or fabricated feedback patterns.",
    "BRAND_IMPERSONATION": "Spoofed official accounts, fake customer support handles, or executive lookalikes.",
    "PHISHING_SCAM": "Fraudulent promotional giveaways, lookalike domains, or phishing landing pages.",
    "REPUTATION_ATTACK": "Coordinated smear campaigns, astroturfed boycotts, or unsubstantiated FUD.",
    "FALSE_CLAIM": "Fabricated claims regarding company bankruptcy, shutdowns, or executive scandals.",
    "PRODUCT_SAFETY": "Hazard claims, battery explosion allegations, toxicity, or unverified recall rumors.",
    "CUSTOMER_COMPLAINT": "Legitimate consumer service/quality grievances (non-malicious operational issues).",
    "REGULATORY_LEGAL": "Official investigations, antitrust lawsuits, regulatory inquiries, or penalties.",
    "LISTING_ABUSE": "Marketplace catalog hijacking, unauthorized bundle alterations, or brand gate evasion.",
    "TRADEMARK_ABUSE": "Unauthorized commercial exploitation of logos, trademarks, or brand assets.",
    "UNVERIFIED_RUMOR": "Speculative unconfirmed discourse circulating across social communities.",
}

KNOWN_BRAND_CATALOG = {
    "NIKE": {"brand": "Nike", "products": ["AIR MAX", "JORDAN", "DUNK", "AIR FORCE 1", "PEGASUS", "TECH FLEECE"]},
    "SAMSUNG": {"brand": "Samsung", "products": ["GALAXY S24", "GALAXY S23", "GALAXY Z FOLD", "GALAXY WATCH", "NEO QLED"]},
    "APPLE": {"brand": "Apple", "products": ["IPHONE 16", "IPHONE 15", "MACBOOK PRO", "AIRPODS", "APPLE WATCH", "IPAD"]},
    "TATA MOTORS": {"brand": "Tata Motors", "products": ["NEXON", "HARRIER", "SAFARI", "TIAGO", "PUNCH", "CURVV", "JLR"]},
    "ZOMATO": {"brand": "Zomato", "products": ["GOLD", "BLINKIT", "HYPERPURE"]},
    "SONY": {"brand": "Sony", "products": ["PLAYSTATION 5", "PS5", "BRAVIA", "WH-1000XM5", "XPERIA"]},
    "TESLA": {"brand": "Tesla", "products": ["MODEL 3", "MODEL Y", "MODEL S", "MODEL X", "CYBERTRUCK", "FSD"]},
    "ADIDAS": {"brand": "Adidas", "products": ["ULTRABOOST", "SAMBA", "STAN SMITH", "YEEZY", "GAZELLE"]},
    "MICROSOFT": {"brand": "Microsoft", "products": ["WINDOWS", "AZURE", "OFFICE", "COPILOT", "XBOX", "SURFACE", "DEFENDER", "TEAMS"]},
}


@dataclass
class BrandThreatRecord:
    threat_id: str
    threat_type: str                         # One of THREAT_TAXONOMY keys
    severity: str                            # "CRITICAL" | "HIGH" | "MEDIUM" | "LOW"
    title: str
    description: str
    platform: str
    evidence_ids: List[str] = field(default_factory=list)
    confidence: float = 0.85
    actionable_recommendation: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "threat_id": self.threat_id,
            "threat_type": self.threat_type,
            "type": self.threat_type,
            "severity": self.severity,
            "title": self.title,
            "description": self.description,
            "platform": self.platform,
            "evidence_ids": self.evidence_ids,
            "confidence": self.confidence,
            "actionable_recommendation": self.actionable_recommendation,
        }


@dataclass
class BrandShieldExtractionResult:
    brand: str
    product: Optional[str] = None
    threats: List[BrandThreatRecord] = field(default_factory=list)
    counterfeits: List[Dict[str, Any]] = field(default_factory=list)
    impersonations: List[Dict[str, Any]] = field(default_factory=list)
    review_patterns: Dict[str, Any] = field(default_factory=dict)
    claims: List[Dict[str, Any]] = field(default_factory=list)
    total_signals_analyzed: int = 0
    extracted_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "brand": self.brand,
            "product": self.product,
            "threats": [t.to_dict() for t in self.threats],
            "counterfeits": self.counterfeits,
            "impersonations": self.impersonations,
            "review_patterns": self.review_patterns,
            "claims": self.claims,
            "total_signals_analyzed": self.total_signals_analyzed,
            "extracted_at": self.extracted_at,
        }
