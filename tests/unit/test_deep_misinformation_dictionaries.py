"""
Tests for Option A: Deep Static & Forensic Dictionary Expansion
Verifies expanded topic context routing, multi-angled contradiction probes,
and agent extractor lexicons across Scout, BrandShield, Personal Watch, and Trending.
"""
from backend.services.research.topic_context import infer_context, TOPICS
from backend.services.agent_reach.source_planner import SourcePlanningEngine
from backend.agents.scout.extraction import ScoutExtractionEngine
from backend.agents.brandshield.extraction import BrandShieldExtractionEngine
from backend.agents.personal_watch.extraction import PersonalWatchExtractionEngine
from backend.agents.trending.extraction import TrendingExtractionEngine
from backend.services.agent_reach.channels import EvidenceFragment


def test_expanded_topic_context_misinformation_categories():
    """Verify new specialized misinformation categories in TOPICS."""
    expected_categories = [
        "financial_misinformation",
        "smear_campaigns",
        "synthetic_media",
        "viral_misinformation",
        "astroturfing",
        "executive_threats",
    ]
    for cat in expected_categories:
        assert cat in TOPICS, f"Missing topic category: {cat}"
        assert len(TOPICS[cat]) >= 4, f"Topic {cat} has insufficient cue phrases"


def test_infer_context_with_misinformation_cues():
    """Verify infer_context activates specialized tasks and scores for misinformation cues."""
    # Financial manipulation
    ctx_fin = infer_context("Whistleblower complaint alleging accounting fraud at TechCorp", "TechCorp", agent="scout")
    assert "FRAUD_INVESTIGATION" in ctx_fin.tasks
    assert "financial_misinformation" in ctx_fin.topics

    # Smear campaign
    ctx_brand = infer_context("Coordinated boycott campaign and smear against BrandX", "BrandX", agent="brandshield")
    assert "SMEAR_CAMPAIGN" in ctx_brand.tasks
    assert "smear_campaigns" in ctx_brand.topics

    # Deepfake / synthetic media
    ctx_pw = infer_context("Viral deepfake video and AI voice clone of ExecutiveY", "ExecutiveY", agent="personal_watch")
    assert "DEEPFAKE_DEFENSE" in ctx_pw.tasks
    assert "synthetic_media" in ctx_pw.topics


def test_source_planner_expanded_terms_and_probes():
    """Verify source planner term sets and multi-angled contradiction probes."""
    engine = SourcePlanningEngine()
    
    assert "short seller" in engine.FINANCIAL_TERMS
    assert "whistleblower" in engine.MISINFORMATION_TERMS
    assert "deepfake video" in [t for t in engine.VIP_DEFAMATION_TERMS] or "voice clone" in engine.VIP_DEFAMATION_TERMS

    # Test scout contradiction probe query formatting for a rumor/claim
    plan_scout = engine.plan("Apple accounting whistleblower rumor", entity="Apple", domain="financial", agent="scout")
    contr_queries = [a.query for a in plan_scout.actions if a.source_category == "contradiction_probe"]
    assert len(contr_queries) >= 1
    # Verify boolean keywords or forensic terms are present
    assert any("short seller" in q or "whistleblower" in q or "rumor" in q for q in contr_queries)


def test_scout_extraction_financial_rumor_lexicon():
    """Verify Scout extractor detects financial rumors from diverse channels beyond just reddit/twitter."""
    extractor = ScoutExtractionEngine()
    fragment = EvidenceFragment(
        evidence_id="ev_scout_1",
        platform="web",
        url="https://finance-news.com/techcorp-rumor",
        title="Whistleblower claims off-balance sheet accounting red flags at TechCorp",
        snippet="Unconfirmed reports allege hidden debt and accounting irregularities.",
        content="Market analysts are reviewing forensic audit concerns.",
    )
    result = extractor.extract([fragment], ticker_or_company="TechCorp")
    assert len(result.rumor_signals) == 1
    assert result.rumor_signals[0]["evidence_ids"] == ["ev_scout_1"]


def test_brandshield_extraction_expanded_abuse_lexicon():
    """Verify BrandShield extractor flags grey-market dupes and customer service phishing."""
    extractor = BrandShieldExtractionEngine()
    frags = [
        EvidenceFragment(
            evidence_id="ev_bs_1",
            platform="web",
            url="https://dupe-shoes.com/product",
            title="LuxuryBrand replica grade 1:1 clone first copy discount",
            snippet="Top tier AAA quality unauthorized dealer.",
            content="Get the exact dupe with free shipping.",
        ),
        EvidenceFragment(
            evidence_id="ev_bs_2",
            platform="twitter",
            url="https://twitter.com/fake_support",
            title="Official customer service scam handle impersonating LuxuryBrand",
            snippet="Send credentials to this support scam account.",
            content="Phishing warning reported by users.",
        ),
    ]
    result = extractor.extract(frags, brand_name="LuxuryBrand")
    assert len(result.threats) >= 1
    types = [t.threat_type for t in result.threats]
    assert any("COUNTERFEIT" in t or "IMPERSONATION" in t for t in types)


def test_personal_watch_extraction_expanded_synthetic_media():
    """Verify Personal Watch extractor catches voice clone and giveaway scams."""
    extractor = PersonalWatchExtractionEngine()
    frag = EvidenceFragment(
        evidence_id="ev_pw_1",
        platform="youtube",
        url="https://youtube.com/watch?v=clone",
        title="VIP Executive AI voice clone crypto giveaway scam streaming live",
        snippet="Fake channel broadcasting synthetic video with face swap.",
        content="Deepfake audio detected by community moderators.",
    )
    result = extractor.extract([frag], person_name="VIP Executive")
    assert len(result.impersonation_alerts) == 1
    assert result.impersonation_alerts[0]["threat_level"] == "HIGH"


def test_trending_extraction_expanded_neg_words():
    """Verify Trending extractor scores sentiment on astroturfed / hoax narratives."""
    extractor = TrendingExtractionEngine()
    frag = EvidenceFragment(
        evidence_id="ev_tr_1",
        platform="twitter",
        url="https://x.com/trend",
        title="Viral hoax debunked: astroturf bot farm spreading manipulated smear",
        snippet="Coordinated inauthentic campaign flagged as misleading.",
        content="Fact checkers confirm fake viral rumor.",
    )
    result = extractor.extract([frag], target_entity="TrendingTopic")
    assert result.sentiment["direction"] == "negative"
    assert result.sentiment["score"] < 0
