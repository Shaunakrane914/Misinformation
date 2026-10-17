"""
Aegis Protocol — Source Quality & Role Classification Engine
============================================================
Classifies external intelligence sources by institutional authority, directness,
and forensic tier, establishing deterministic quality scoring.
"""

import re
import urllib.parse
from typing import Any, Dict, List, Optional, Set, Tuple

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

ENCYCLOPEDIA_DOMAINS: Set[str] = {
    "wikipedia.org", "wikimedia.org", "wiktionary.org", "britannica.com"
}

# Explicit identity knowledge, not a heuristic derived from a queried name.
# Deployments can inject additional verified mappings into SourceQualityEngine.
VERIFIED_CORPORATE_DOMAINS = {
    "infosys": {"infosys.com"},
    "tatamotors": {"tatamotors.com"},
    "tesla": {"tesla.com"},
    "nvidia": {"nvidia.com"},
    "apple": {"apple.com"},
    "microsoft": {"microsoft.com", "windows.com", "azure.com", "office.com"},
    "anthropic": {"anthropic.com"},
    "amazon": {"amazon.com", "aboutamazon.com"},
    "google": {"google.com", "deepmind.google"},
    "alphabet": {"abc.xyz", "google.com"},
    "meta": {"meta.com", "about.fb.com", "facebook.com"},
    "openai": {"openai.com"},
}


def canonical_hostname(url: str) -> str:
    """Parse a public URL identity without granting trust to URL text or userinfo."""
    try:
        parsed = urllib.parse.urlsplit(url or "")
        _ = parsed.port
        if parsed.scheme.lower() not in {"http", "https"} or parsed.username or parsed.password:
            return ""
        host = (parsed.hostname or "").rstrip(".").encode("idna").decode("ascii").lower()
        if not host or any(not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]*[a-z0-9])?", label)
                           for label in host.split(".")):
            return ""
        return host
    except (ValueError, UnicodeError):
        return ""


def hostname_matches(host: str, trusted: str) -> bool:
    host, trusted = host.rstrip(".").lower(), trusted.rstrip(".").lower()
    return bool(trusted) and (host == trusted or host.endswith("." + trusted))


def _matches_registry(host: str, registry) -> bool:
    return any(hostname_matches(host, trusted) for trusted in registry)


def registered_authority_url(url: str) -> bool:
    """Registry ownership hint for candidate routing, never claim confirmation."""
    host = canonical_hostname(url)
    return _matches_registry(host, REGULATORY_GOVERNMENT_DOMAINS) or any(
        _matches_registry(host, domains) for domains in VERIFIED_CORPORATE_DOMAINS.values()
    )


class UtilityUrlCheck(tuple):
    """Dual-mode return type: supports both tuple unpacking (bool, str) and boolean evaluation."""
    def __new__(cls, is_utility: bool, utility_type: str = ""):
        return super().__new__(cls, (is_utility, utility_type))

    def __bool__(self) -> bool:
        return bool(self[0])


def is_utility_or_auth_url(url: str) -> UtilityUrlCheck:
    """
    Check if URL represents an authentication portal, login screen, account manager,
    or app storefront utility page.
    """
    if not url:
        return UtilityUrlCheck(False, "")
    try:
        parsed = urllib.parse.urlsplit(url.lower())
        host = (parsed.hostname or "").lower()
        path = (parsed.path or "").lower()
    except Exception:
        return UtilityUrlCheck(False, "")

    # Login / Auth hostnames
    if any(host == p or host.startswith(p + ".") or f".{p}." in host for p in ("account", "myaccount", "login", "signin", "auth", "sso", "oauth", "identity", "accounts")):
        return UtilityUrlCheck(True, "AUTH_PORTAL")

    # Login / Auth paths
    if any(seg in path for seg in ("/login", "/signin", "/sign-in", "/myaccount", "/auth", "/sso", "/oauth")):
        return UtilityUrlCheck(True, "AUTH_PORTAL")

    # Store / App Catalog hostnames & paths
    if any(host == p or host.startswith(p + ".") for p in ("apps", "store", "play.google.com")):
        return UtilityUrlCheck(True, "APP_CATALOG")
    if path.startswith("/store") or path.startswith("/apps") or (path.startswith("/home") and _matches_registry(host, {"microsoft.com", "apple.com", "google.com"})):
        return UtilityUrlCheck(True, "APP_CATALOG")

    return UtilityUrlCheck(False, "")


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
        # Web redirects are observed by the transport. Publisher-declared
        # canonical metadata cannot override that observed origin.
        url = item.metadata.get("observed_final_endpoint") or item.canonical_url or ""
        domain = canonical_hostname(url)
        # A supplied source_domain cannot override the actual source URL.
        item.source_domain = domain
        item.primary_source = False
        item.official_source = False

        title_lower = (item.title or "").lower()
        snippet_lower = (item.snippet or "").lower()
        content_lower = (item.content or "").lower()
        full_text = f"{domain} {title_lower} {snippet_lower} {content_lower[:400]}"

        # Clean target name for matching official domains
        # Resolved financial entities may retain a parenthesized ticker. It is
        # an alias, not part of the ownership-registry key.
        registry_name = re.sub(r"\([^)]*\)", "", target_name)
        clean_target = re.sub(r'[^a-z0-9]', '', registry_name.lower()) if target_name else ""
        
        # 1. Detect Utility / Auth / Store / Encyclopedia
        is_utility = is_utility_or_auth_url(url)
        is_encyclopedia = _matches_registry(domain, ENCYCLOPEDIA_DOMAINS)

        # 2. Detect Official Corporate Domain
        is_official = _matches_registry(domain, self.official_domains.get(clean_target, set()))

        # 3. Regulatory & Government Filings
        is_regulatory = _matches_registry(domain, REGULATORY_GOVERNMENT_DOMAINS)
        filing_markers = [
            "form 10-k", "form 10-q", "form 8-k", "regulatory filing", "exchange filing",
            "bse filing", "nse filing", "sec filing", "court order", "consent decree"
        ]
        has_filing_marker = any(fm in full_text for fm in filing_markers)

        # 4. Assign Role, Tier, and Base Quality Score
        if is_utility:
            item.source_role = SourceRole.UTILITY_PORTAL.value
            item.source_tier = SourceTier.TIER_4_UTILITY.value
            item.primary_source = False
            item.official_source = False
            base_score = 0.15

        elif is_regulatory:
            path = urllib.parse.urlsplit(url).path.lower().rstrip("/")
            is_index = path in {"", "/search", "/edgar", "/edgar/search", "/filings"} or "/submissions/" in path
            is_metadata = item.content_depth in {ContentDepth.DIRECT_METADATA.value, ContentDepth.HEADLINE_ONLY.value}
            is_document = bool(not is_index and not is_metadata and (
                has_filing_marker or path.endswith((".htm", ".html", ".pdf", ".xml")) or "/filing" in path
                or re.search(r"/edgar/(?:10k|10q|8k)(?:/|$)", path)
            ))
            item.metadata["authority_scope"] = "REGULATORY_DOCUMENT" if is_document else "REGULATOR_REFERENCE"
            item.source_role = SourceRole.PRIMARY.value if is_document else SourceRole.DISCOVERY.value
            item.source_tier = SourceTier.TIER_1_OFFICIAL_FILING.value if is_document else SourceTier.TIER_3_AGGREGATE.value
            item.primary_source = is_document
            item.official_source = True
            base_score = 0.98 if is_document else 0.60

        elif is_official:
            path = urllib.parse.urlsplit(url).path.lower().strip("/")
            is_landing = not path or bool(re.fullmatch(r"[a-z]{2}(?:[-/][a-z]{2})?", path))
            item.metadata["authority_scope"] = "CORPORATE_LANDING" if is_landing else "CORPORATE_DOCUMENT"
            item.source_role = SourceRole.DISCOVERY.value if is_landing else SourceRole.PRIMARY.value
            item.source_tier = SourceTier.TIER_3_AGGREGATE.value if is_landing else SourceTier.TIER_1_ORIGINAL_DOCUMENT.value
            item.primary_source = not is_landing
            item.official_source = True
            base_score = 0.60 if is_landing else 0.92

        elif is_encyclopedia:
            item.source_role = SourceRole.AGGREGATOR.value
            item.source_tier = SourceTier.TIER_3_AGGREGATE.value
            item.primary_source = False
            item.official_source = False
            base_score = 0.60

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


def classify_and_score(url: str, target_name: str = "", title: str = "", content: str = "") -> Dict[str, Any]:
    """Helper function to classify and score a URL/snippet directly."""
    item = EvidenceItem(
        id="probe",
        title=title,
        content=content,
        snippet=content[:200] if content else title,
        canonical_url=url,
        channel="web",
    )
    res = source_quality_engine.classify_and_score(item, target_name=target_name)
    return {
        "source_role": SourceRole(res.source_role) if res.source_role in [e.value for e in SourceRole] else res.source_role,
        "source_tier": SourceTier(res.source_tier) if res.source_tier in [e.value for e in SourceTier] else res.source_tier,
        "primary_source": res.primary_source,
        "official_source": res.official_source,
        "quality_score": res.source_quality_score,
        "item": res,
    }
