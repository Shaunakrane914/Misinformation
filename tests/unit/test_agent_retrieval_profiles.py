"""
Aegis Protocol — Agent Retrieval Profiles & Customization Tests
===============================================================
Validates that:
  1. Each of the four domain agents possesses a customized RetrievalProfile
  2. Domain profiles specify distinct required fields, preferred platforms, and content depth
  3. Custom acquisition implementations (BrandShieldAcquisition, TrendingAcquisition, etc.)
     implement the standard AgentAcquisitionBase contract
  4. RetrievalRequest encapsulates domain profiles without leaking across agents
"""

import pytest
from backend.services.agent_reach.channels import AgentAcquisitionBase, RetrievalProfile, RetrievalRequest
from backend.services.agent_reach.profile import (
    BRANDSHIELD_PROFILE,
    PERSONAL_WATCH_PROFILE,
    SCOUT_PROFILE,
    TRENDING_PROFILE,
    BrandShieldAcquisition,
    PersonalWatchAcquisition,
    ScoutAcquisition,
    TrendingAcquisition,
    get_agent_profile,
)


def test_agent_profiles_have_distinct_customizations():
    """
    Ensure the four agents do not use identical retrieval profiles (Section 10-15).
    """
    # 1. BrandShield profile focuses on product/seller/counterfeit
    assert "brand" in BRANDSHIELD_PROFILE.required_fields
    assert "seller" in BRANDSHIELD_PROFILE.required_fields
    assert "product" in BRANDSHIELD_PROFILE.required_fields
    assert BRANDSHIELD_PROFILE.content_depth == "PARTIAL_CONTENT"
    assert BRANDSHIELD_PROFILE.need_comments is True

    # 2. Trending profile focuses on engagement and narrative flow
    assert "engagement" in TRENDING_PROFILE.required_fields
    assert "narrative" in TRENDING_PROFILE.required_fields
    assert TRENDING_PROFILE.content_depth == "SNIPPET"
    assert TRENDING_PROFILE.need_engagement is True

    # 3. Scout profile focuses on financial numbers, earnings, M&A
    assert "financial_facts" in SCOUT_PROFILE.required_fields
    assert "earnings" in SCOUT_PROFILE.required_fields
    assert "corporate_events" in SCOUT_PROFILE.required_fields
    assert SCOUT_PROFILE.content_depth == "FULL_ARTICLE"
    assert SCOUT_PROFILE.need_primary_source is True
    assert SCOUT_PROFILE.need_structured_metadata is True

    # 4. Personal Watch profile focuses on public statements & executive movement
    assert "identity" in PERSONAL_WATCH_PROFILE.required_fields
    assert "public_statement" in PERSONAL_WATCH_PROFILE.required_fields
    assert "career_movement" in PERSONAL_WATCH_PROFILE.required_fields
    assert PERSONAL_WATCH_PROFILE.extraction_hints.get("filter_sensitive_pii") is True


def test_get_agent_profile_lookup():
    """Verify helper lookup retrieves the correct domain profile."""
    assert get_agent_profile("brandshield").agent == "brandshield"
    assert get_agent_profile("trending").agent == "trending"
    assert get_agent_profile("scout").agent == "scout"
    assert get_agent_profile("personal").agent == "personal"
    # Fallback to generic
    assert get_agent_profile("unknown").agent == "unknown"


def test_custom_acquisitions_implement_agent_acquisition_base():
    """
    Verify all 4 domain acquisitions implement AgentAcquisitionBase (Section 20).
    """
    brand_acq = BrandShieldAcquisition()
    trend_acq = TrendingAcquisition()
    scout_acq = ScoutAcquisition()
    personal_acq = PersonalWatchAcquisition()

    for acq in [brand_acq, trend_acq, scout_acq, personal_acq]:
        assert isinstance(acq, AgentAcquisitionBase)
        assert isinstance(acq.get_profile(), RetrievalProfile)
        health = acq.health()
        assert "status" in health
        caps = acq.capabilities()
        assert "required_fields" in caps
        assert "content_depth" in caps


def test_retrieval_request_serialization_with_profile():
    """Verify RetrievalRequest serializes profile cleanly."""
    req = RetrievalRequest(
        agent="scout",
        entity="NVDA",
        intent="earnings report",
        profile=SCOUT_PROFILE,
    )
    data = req.to_dict()
    assert data["agent"] == "scout"
    assert data["profile"] is not None
    assert data["profile"]["content_depth"] == "FULL_ARTICLE"
    assert "financial_facts" in data["profile"]["required_fields"]


def test_brandshield_acquisition_behavioral_customization():
    """Verify BrandShieldAcquisition marketplace and complaint extraction behavior."""
    from backend.services.agent_reach.channels import FetchedDocument, CandidateSource
    acq = BrandShieldAcquisition()
    cand = CandidateSource(url="https://amazon.com/dp/B000TEST", platform="web", title="Official Brand Sneakers $120.00")
    cand.metadata["is_marketplace"] = True
    doc = FetchedDocument(url=cand.url, status="SUCCESS", raw_content="Fake knockoff review complaint for $89.99. Customer reported fake knockoff.")
    req = RetrievalRequest(agent="brandshield", entity="BrandX", intent="reviews")

    frags = acq.normalize(doc, cand, req)
    assert len(frags) > 0
    f = frags[0]
    assert f.content_depth == "PARTIAL_CONTENT"
    assert f.metadata.get("marketplace_listing") is True
    assert "counterfeit_indicators" in f.metadata
    assert "price" in f.metadata


def test_trending_acquisition_behavioral_customization():
    """Verify TrendingAcquisition social origin and wire syndication tagging."""
    from backend.services.agent_reach.channels import FetchedDocument, CandidateSource
    acq = TrendingAcquisition()
    cand = CandidateSource(url="https://reuters.com/article/tech-update", platform="news", title="Tech News")
    doc = FetchedDocument(url=cand.url, status="SUCCESS", raw_content="Reuters tech news breaking story", raw_metadata={"likes": 1200, "views": 50000})
    req = RetrievalRequest(agent="trending", entity="Tech", intent="trends")

    frags = acq.normalize(doc, cand, req)
    assert len(frags) > 0
    f = frags[0]
    assert f.content_depth == "SNIPPET"
    assert f.metadata.get("is_wire_syndication") is True
    assert f.metadata.get("likes") == 1200


def test_scout_acquisition_behavioral_customization():
    """Verify ScoutAcquisition primary filing classification and full article depth."""
    from backend.services.agent_reach.channels import FetchedDocument, CandidateSource
    acq = ScoutAcquisition()
    cand = CandidateSource(url="https://sec.gov/edgar/data/0001/10-k.htm", platform="web", title="10-K Annual Report")
    doc = FetchedDocument(url=cand.url, status="SUCCESS", raw_content="Full annual report body with $1.4B revenue.")
    req = RetrievalRequest(agent="scout", entity="Company", intent="10-K")

    frags = acq.normalize(doc, cand, req)
    assert len(frags) > 0
    f = frags[0]
    assert f.content_depth == "FULL_ARTICLE"
    assert f.metadata.get("is_primary_source") is True
    assert f.metadata.get("financial_domain") is True


def test_personal_watch_acquisition_pii_sanitization():
    """Verify PersonalWatchAcquisition actively redacts sensitive private PII."""
    from backend.services.agent_reach.channels import FetchedDocument, CandidateSource
    acq = PersonalWatchAcquisition()
    cand = CandidateSource(url="https://example.com/exec-profile", platform="web", title="Executive Profile")
    doc = FetchedDocument(
        url=cand.url,
        status="SUCCESS",
        raw_content="CEO John Doe can be reached at 555-123-4567 or SSN 123-45-6789 living at 742 Evergreen Terrace.",
    )
    req = RetrievalRequest(agent="personal", entity="John Doe", intent="profile")

    frags = acq.normalize(doc, cand, req)
    assert len(frags) > 0
    f = frags[0]
    assert f.metadata.get("pii_filtered") is True
    assert "555-123-4567" not in f.content
    assert "[REDACTED_PHONE]" in f.content
    assert "123-45-6789" not in f.content
    assert "[REDACTED_SSN]" in f.content
    assert "742 Evergreen Terrace" not in f.content

