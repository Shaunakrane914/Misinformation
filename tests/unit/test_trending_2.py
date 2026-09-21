"""
Unit tests for Trending Agent 2.0: Trend Discovery + Trend Intelligence Engine.
Validates entity resolution, mode detection, query planning, evidence normalization,
clustering, syndication detection, velocity/snapshot tracking, claim extraction,
sentiment vs misinformation separation, and zero hallucination guarantees.
"""

import pytest
from backend.agents.trending_agent import (
    TrendingAgent,
    TrendEvidence,
    Trend,
    KNOWN_ENTITY_CATALOG
)
from backend.services.agent_reach.planner import RetrievalPlanner


@pytest.fixture
def agent():
    return TrendingAgent()


@pytest.fixture
def planner():
    return RetrievalPlanner()


def test_entity_resolution(agent: TrendingAgent):
    """Test entity resolution from known catalog and normalization."""
    # Test Deepika Padukone
    res_deepika = agent.resolve_entity("Deepika")
    assert res_deepika["mode"] == "entity"
    assert res_deepika["resolved_entity"] == "Deepika Padukone"
    assert "Deepika" in res_deepika["aliases"]
    assert res_deepika["category"] == "entertainment"

    # Test Shah Rukh Khan
    res_srk = agent.resolve_entity("SRK")
    assert res_srk["mode"] == "entity"
    assert res_srk["resolved_entity"] == "Shah Rukh Khan"

    # Test OpenAI
    res_openai = agent.resolve_entity("OpenAI")
    assert res_openai["mode"] == "entity"
    assert res_openai["resolved_entity"] == "OpenAI"
    assert res_openai["category"] == "technology"


def test_mode_detection(agent: TrendingAgent):
    """Test automatic detection of Entity Mode vs Discovery Mode."""
    # Discovery questions
    disc_1 = agent.resolve_entity("What's trending in India?")
    assert disc_1["mode"] == "discovery"
    assert "Trending in India" in disc_1["resolved_entity"]

    disc_2 = agent.resolve_entity("viral entertainment today")
    assert disc_2["mode"] == "discovery"

    # Entity input
    ent_1 = agent.resolve_entity("Jawan")
    assert ent_1["mode"] == "entity"
    assert ent_1["resolved_entity"] == "Jawan (Film)"


def test_trending_query_classes(planner: RetrievalPlanner):
    """Test bounded query planning for both modes."""
    # Entity mode query classes
    classes_ent = planner.build_trending_query_classes("Deepika Padukone", is_discovery=False)
    assert "general_buzz" in classes_ent
    assert "viral_moments" in classes_ent
    assert "controversy_rumors" in classes_ent
    assert "announcements_projects" in classes_ent
    assert "community_discourse" in classes_ent
    assert "claim_verification" in classes_ent
    assert any("Deepika Padukone" in q for q in classes_ent["general_buzz"])

    # Discovery mode query classes
    classes_disc = planner.build_trending_query_classes("What's trending in India?", is_discovery=True)
    assert "regional_trends" in classes_disc
    assert "domain_trends" in classes_disc
    assert "breaking_headlines" in classes_disc
    assert "social_momentum" in classes_disc
    assert any("India" in q for q in classes_disc["regional_trends"])


def test_evidence_normalization_and_url_preservation(agent: TrendingAgent):
    """Test evidence normalization preserves real URLs and discards '#'."""
    raw_sample = [
        {
            "title": "Major Film Announcement Confirmed",
            "snippet": "Production house officially greenlights new historical drama.",
            "url": "https://reuters.com/entertainment/film-announcement-123",
            "source": "Reuters",
            "author": "Film Desk",
            "published": "2026-09-21T10:00:00Z"
        },
        {
            "title": "Fan speculation on casting choices",
            "snippet": "Reddit community debates potential cast members.",
            "url": "#",  # Invalid placeholder URL
            "source": "Reddit r/bollywood",
            "author": "u/cinema_fan",
            "published": "2026-09-21T11:00:00Z"
        }
    ]

    normalized = agent._normalize_evidence(raw_sample, "news")
    assert len(normalized) == 2

    # First item has real URL and PRIMARY / TIER_1 rating
    assert normalized[0].url == "https://reuters.com/entertainment/film-announcement-123"
    assert normalized[0].source_role == "PRIMARY"
    assert normalized[0].source_tier == "TIER_1"

    # Second item rejected '#' and marked unavailable
    assert normalized[1].url == "Source URL unavailable"
    assert normalized[1].canonical_url == ""


def test_source_independence_syndication(agent: TrendingAgent):
    """Test syndicated wire reports are grouped together under same source_group_id."""
    raw_wire = [
        {
            "title": "Actor receives prestigious global cinematic award",
            "url": "https://outlet1.com/story",
            "source": "Press Trust of India (PTI)",
            "published": "2026-09-21T10:00:00Z"
        },
        {
            "title": "Actor receives prestigious global cinematic award",
            "url": "https://outlet2.com/story",
            "source": "ANI Wire Services",
            "published": "2026-09-21T10:05:00Z"
        }
    ]

    norm = agent._normalize_evidence(raw_wire, "news")
    # Wire signatures should result in wire group IDs
    assert norm[0].source_group_id.startswith("G-WIRE")
    assert norm[1].source_group_id.startswith("G-WIRE")


def test_trend_clustering(agent: TrendingAgent):
    """Test grouping of evidence into structured Trend objects."""
    evidence = [
        TrendEvidence(
            evidence_id="EV-001",
            platform="news",
            source="The Hindu",
            title="Director announces new upcoming film project with actor",
            content="Official press release reveals next summer release date.",
            snippet="Official press release reveals next summer release date.",
            url="https://thehindu.com/project-123",
            canonical_url="https://thehindu.com/project-123",
            author="Staff",
            published_at="2026-09-21T09:00:00Z",
            retrieved_at="2026-09-21T09:30:00Z",
            source_role="SECONDARY",
            source_tier="TIER_2",
            source_group_id="G-001",
            retrieval_method="agent_reach"
        ),
        TrendEvidence(
            evidence_id="EV-002",
            platform="reddit",
            source="r/bollywood",
            title="Discussion on director's announcement and release",
            content="Fans reacting to the upcoming film project announcement.",
            snippet="Fans reacting to the announcement.",
            url="https://reddit.com/r/bollywood/comments/abc",
            canonical_url="https://reddit.com/r/bollywood/comments/abc",
            author="u/fan",
            published_at="2026-09-21T09:15:00Z",
            retrieved_at="2026-09-21T09:30:00Z",
            source_role="COMMUNITY",
            source_tier="TIER_4",
            source_group_id="G-002",
            retrieval_method="agent_reach"
        )
    ]

    entity_info = {"resolved_entity": "Deepika Padukone", "mode": "entity"}
    trends = agent._cluster_trends(evidence, entity_info)

    assert len(trends) >= 1
    t = trends[0]
    assert t.topic.startswith("Deepika Padukone:")
    assert t.signal_count == 2
    assert t.unique_source_count == 2
    assert t.platform_count == 2
    assert t.origin["first_observed_source"] == "The Hindu"
    assert t.origin["first_observed_platform"] == "news"


def test_claim_extraction_and_status(agent: TrendingAgent):
    """Test that claims extract verification statuses based on source role."""
    evidence_unverified = [
        TrendEvidence(
            evidence_id="EV-001",
            platform="twitter",
            source="X User",
            title="Rumor: Actor secretly signed for unconfirmed cameo",
            content="Speculation on social media.",
            snippet="Speculation.",
            url="https://x.com/user/123",
            canonical_url="https://x.com/user/123",
            author="@user",
            published_at="2026-09-21T10:00:00Z",
            retrieved_at="2026-09-21T10:05:00Z",
            source_role="COMMUNITY",
            source_tier="TIER_4",
            source_group_id="G-001",
            retrieval_method="agent_reach"
        )
    ]

    claims = agent._extract_claims_from_cluster(evidence_unverified)
    assert len(claims) == 1
    assert claims[0]["status"] == "UNVERIFIED"
    assert claims[0]["supporting_sources"] == 0


def test_sentiment_vs_misinformation_separation(agent: TrendingAgent):
    """Test that negative movie reviews or criticism are NOT flagged as high misinformation."""
    negative_criticism = [
        TrendEvidence(
            evidence_id="EV-001",
            platform="news",
            source="Film Companion",
            title="Film review: Disappointing screenplay and poor performances",
            content="Critics criticize the terrible dialogue and slow pacing.",
            snippet="Critics criticize the screenplay.",
            url="https://filmcompanion.com/review",
            canonical_url="https://filmcompanion.com/review",
            author="Critic",
            published_at="2026-09-21T10:00:00Z",
            retrieved_at="2026-09-21T10:05:00Z",
            source_role="COMMENTARY",
            source_tier="TIER_2",
            source_group_id="G-001",
            retrieval_method="agent_reach"
        )
    ]

    claims = agent._extract_claims_from_cluster(negative_criticism)
    sent_label, sent_score = agent._compute_cluster_sentiment(negative_criticism)
    misinfo_risk, rationale = agent._evaluate_misinformation_risk(negative_criticism, claims)

    # Negative sentiment should NOT lead to HIGH misinformation risk!
    assert sent_label == "NEGATIVE"
    assert misinfo_risk == "LOW"
    assert "critical discussion" in rationale.lower() or "credible reporting" in rationale.lower()


def test_velocity_and_snapshot_persistence(agent: TrendingAgent):
    """Test velocity calculations and snapshot storage across multiple scans."""
    topic = "Major Project Announcement"

    # Scan 1: initial observation
    vel_1 = agent._calculate_velocity(topic, signal_count=10, source_count=4, platform_count=2)
    assert vel_1["status"] == "EMERGING"
    assert len(vel_1["history"]) == 1

    # Scan 2: growth observation
    vel_2 = agent._calculate_velocity(topic, signal_count=15, source_count=6, platform_count=3)
    assert vel_2["growth_rate_pct"] == 50.0
    assert vel_2["status"] == "ACCELERATING"
    assert len(vel_2["history"]) == 2


def test_box_office_integrity(agent: TrendingAgent):
    """Test that box office handling reports unavailable rather than fake numbers."""
    bo_result = agent.fetch_box_office("Jawan")
    assert bo_result["status"] == "unavailable"
    assert "unavailable" in bo_result["message"].lower()
    assert bo_result["net_india"] == "N/A"
    assert bo_result["gross_worldwide"] == "N/A"
