"""
Aegis Protocol — Source Quality & Role Classification Engine
============================================================
Classifies external intelligence sources by institutional authority, directness,
and forensic tier, establishing deterministic quality scoring.
"""

import re
import urllib.parse
from typing import Dict, List, Optional, Set, Tuple

from backend.services.research.research_models import (
    ContentDepth,
    EvidenceItem,
    SourceRole,
    SourceTier,
)

# ── Authority Domain Registries ───────────────────────────────────────────────

REGULATORY_GOVERNMENT_DOMAINS: Set[str] = {
    "sec.gov", "bseindia.com", "nseindia.com", "sebi.gov.in", "rbi.org.in",
    "fda.gov", "cpsc.gov", "ftc.gov", "fcc.gov", "justice.gov", "supremecourt.gov",
    "gov.uk", "fca.org.uk", "esma.europa.eu", "who.int", "cdc.gov", "nih.gov",
    "wipo.int", "uspto.gov", "nhtsa.gov", "ec.europa.eu", "whitehouse.gov"
}

TIER1_PRESS_DOMAINS: Set[str] = {
    "reuters.com", "apnews.com", "bloomberg.com", "ft.com", "wsj.com",
    "economictimes.indiatimes.com", "livemint.com", "business-standard.com",
    "moneycontrol.com", "cnbc.com", "bbc.com", "thehindu.com", "nytimes.com",
    "theguardian.com", "washingtonpost.com", "hindustantimes.com", "indianexpress.com",
    "ndtv.com", "cnbctv18.com", "financialexpress.com"
}

SPECIALIZED_TECH_INDUSTRY_DOMAINS: Set[str] = {
    "techcrunch.com", "arstechnica.com", "theverge.com", "wired.com", "coindesk.com",
    "cointelegraph.com", "nature.com", "science.org", "sciencedirect.com",
    "biorxiv.org", "arxiv.org", "github.com", "electrek.co", "autocarindia.com",
    "carandbike.com", "sneakersnews.com", "complex.com", "variety.com", "deadline.com"
}

AGGREGATOR_CONTENT_DOMAINS: Set[str] = {
    "msn.com", "yahoo.com", "news.google.com", "bing.com", "aol.com", "duckduckgo.com"
}

COMMUNITY_DOMAINS: Set[str] = {
    "reddit.com", "news.ycombinator.com", "quora.com", "pullpush.io", "v2ex.com"
}

SOCIAL_DOMAINS: Set[str] = {
    "twitter.com", "x.com", "youtube.com", "youtu.be", "instagram.com", "tiktok.com"
}

# Explicit identity knowledge, not a heuristic derived from a queried name.
# Deployments can inject additional verified mappings into SourceQualityEngine.
VERIFIED_CORPORATE_DOMAINS = {
    "tesla": {"tesla.com"},
    "nvidia": {"nvidia.com"},
    "apple": {"apple.com"},
    "microsoft": {"microsoft.com"},
    "anthropic": {"anthropic.com"},
}


def hostname_matches(host: str, trusted: str) -> bool:
    host, trusted = host.rstrip(".").lower(), trusted.rstrip(".").lower()
    return bool(trusted) and (host == trusted or host.endswith("." + trusted))


def _matches_registry(host: str, registry) -> bool:
    return any(hostname_matches(host, trusted) for trusted in registry)


class SourceQualityEngine:
    """Classifies source roles, forensic tiers, and calculates source quality scores."""

    def __init__(self, official_domains=None):
        self.official_domains = {
            re.sub(r"[^a-z0-9]", "", name.lower()): set(domains)
            for name, domains in (official_domains if official_domains is not None
                                  else VERIFIED_CORPORATE_DOMAINS).items()
        }

    def classify_and_score(self, item: EvidenceItem, target_name: str = "") -> EvidenceItem:
        """
        Assigns source_role, source_tier, official/primary flags,
        and computes source_quality_score (0.0 to 1.0).
        """
        url = (item.canonical_url or "").lower()
        try:
            parsed = urllib.parse.urlsplit(url)
            # Trigger urllib's numeric/range validation for explicitly supplied ports.
            _ = parsed.port
            domain = (parsed.hostname or "").lower().rstrip(".")
            if parsed.scheme not in ("http", "https") or parsed.username or parsed.password:
                domain = ""
        except ValueError:
            domain = ""
        # A supplied source_domain cannot override the actual source URL.
        item.source_domain = domain
        item.primary_source = False
        item.official_source = False

        title_lower = (item.title or "").lower()
        snippet_lower = (item.snippet or "").lower()
        content_lower = (item.content or "").lower()
        full_text = f"{domain} {title_lower} {snippet_lower} {content_lower[:400]}"

        # Clean target name for matching official domains
        clean_target = re.sub(r'[^a-z0-9]', '', target_name.lower()) if target_name else ""
        
        # 1. Detect Official Corporate Domain
        is_official = _matches_registry(domain, self.official_domains.get(clean_target, set()))

        # 2. Regulatory & Government Filings
        is_regulatory = _matches_registry(domain, REGULATORY_GOVERNMENT_DOMAINS)
        filing_markers = [
            "form 10-k", "form 10-q", "form 8-k", "regulatory filing", "exchange filing",
            "annual report", "press release", "bse filing", "nse filing", "sec filing",
            "court order", "consent decree", "official announcement"
        ]
        has_filing_marker = any(fm in full_text for fm in filing_markers)

        # 3. Assign Role, Tier, and Base Quality Score
        if is_regulatory or (is_official and has_filing_marker):
            item.source_role = SourceRole.PRIMARY.value
            item.source_tier = SourceTier.TIER_1_OFFICIAL_FILING.value
            item.primary_source = True
            item.official_source = True
            base_score = 0.98

        elif is_official:
            item.source_role = SourceRole.PRIMARY.value
            item.source_tier = SourceTier.TIER_1_ORIGINAL_DOCUMENT.value
            item.primary_source = True
            item.official_source = True
            base_score = 0.92

        elif hostname_matches(domain, "github.com"):
            item.source_role = SourceRole.PRIMARY.value
            item.source_tier = SourceTier.TIER_1_ORIGINAL_DOCUMENT.value
            item.primary_source = True
            base_score = 0.88

        elif _matches_registry(domain, TIER1_PRESS_DOMAINS):
            item.source_role = SourceRole.SECONDARY.value
            item.source_tier = SourceTier.TIER_2_FINANCIAL_PRESS.value
            base_score = 0.82

        elif _matches_registry(domain, SPECIALIZED_TECH_INDUSTRY_DOMAINS):
            item.source_role = SourceRole.SECONDARY.value
            item.source_tier = SourceTier.TIER_2_INVESTIGATIVE.value
            base_score = 0.75

        elif _matches_registry(domain, COMMUNITY_DOMAINS) or item.channel in ("reddit", "hackernews"):
            item.source_role = SourceRole.COMMUNITY.value
            item.source_tier = SourceTier.TIER_3_INVESTOR_COMMUNITY.value
            base_score = 0.50

        elif _matches_registry(domain, SOCIAL_DOMAINS) or item.channel in ("twitter", "youtube", "tiktok", "instagram"):
            if hostname_matches(domain, "youtube.com") or item.channel == "youtube":
                item.source_role = SourceRole.SECONDARY.value
                item.source_tier = SourceTier.TIER_2_VIDEO_ANALYSIS.value
                base_score = 0.58
            else:
                item.source_role = SourceRole.COMMENTARY.value
                item.source_tier = SourceTier.TIER_3_SOCIAL_SIGNALS.value
                base_score = 0.45

        elif _matches_registry(domain, AGGREGATOR_CONTENT_DOMAINS):
            item.source_role = SourceRole.AGGREGATOR.value
            item.source_tier = SourceTier.TIER_3_AGGREGATE.value
            base_score = 0.60

        else:
            item.source_role = SourceRole.DISCOVERY.value
            item.source_tier = SourceTier.TIER_3_AGGREGATE.value
            base_score = 0.55

        # 4. Depth Adjustment
        depth_modifier = 0.0
        if item.content_depth == ContentDepth.FULL_ARTICLE.value:
            depth_modifier = 0.08
        elif item.content_depth == ContentDepth.PARTIAL_CONTENT.value:
            depth_modifier = 0.03
        elif item.content_depth == ContentDepth.HEADLINE_ONLY.value:
            depth_modifier = -0.10

        item.source_quality_score = max(0.10, min(1.0, base_score + depth_modifier))
        return item


source_quality_engine = SourceQualityEngine()
