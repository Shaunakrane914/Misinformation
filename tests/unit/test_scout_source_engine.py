"""
Aegis Protocol — Unit & Regression Tests: Scout Source Acquisition Engine
==========================================================================
Tests:
1. Hard Gates: Platform scope (r/investing vs r/privacy), URL structure (/comments/, /status/).
2. Anti-Token-Cheat Protection: Satya Nadella, Sam Altman, Jensen Huang disambiguation.
3. Domain Integrity Gate: Rejecting corporate homepages when social evidence is requested.
4. Structured Financial Number Extraction: $5.4B, ₹10,000 crore, 200 bps, EPS, currencies.
5. Corporate Event Extraction: GUIDANCE_CHANGE, EARNINGS, M&A, CAPEX_CHANGE, LAYOFF.
6. Temporal Disambiguation: published_at vs event_at.
7. Wire Syndication & Deduplication Clustering: Reuters / AP / PR Newswire echoes into single clusters.
8. Contradiction Detection: Deal size $2B vs $3B without destructive averaging.
9. Rumor vs. Confirmed Epistemic Status.
10. The Ten Canonical Audit Regression Traps.
11. End-to-end ScoutSourceEngine execution & telemetry.
"""

import pytest
from backend.services.agent_reach.scout.models import (
    CandidateSource,
    CorporateEventType,
    EpistemicStatus,
    FactDirection,
    ScoutEvidence,
    ScoutFailureCode,
    ScoutSourceRequest,
    SourceTier,
)
from backend.services.agent_reach.scout.ranking import scout_ranking_engine
from backend.services.agent_reach.scout.extraction import (
    financial_number_extractor,
    corporate_event_extractor,
    temporal_extractor,
    structured_metadata_extractor,
)
from backend.services.agent_reach.scout.deduplication import scout_deduplicator
from backend.services.agent_reach.scout.corroboration import scout_corroboration_engine
from backend.services.agent_reach.scout.engine import scout_source_engine


# ─────────────────────────────────────────────────────────────────────────────
# 1. HARD GATES & SCOPE TESTS
# ─────────────────────────────────────────────────────────────────────────────

def test_hard_gate_reddit_scope_mismatch():
    """Requesting r/investing must HARD REJECT r/privacy."""
    req = ScoutSourceRequest(
        query="portfolio diversification",
        requested_scope="r/investing",
        platform_hint="reddit"
    )
    bad_cand = CandidateSource(
        url="https://www.reddit.com/r/privacy/comments/abc123/protect_financial_data/",
        canonical_url="https://www.reddit.com/r/privacy/comments/abc123/protect_financial_data/",
        platform="reddit",
        source_type="post",
        external_id="abc123",
        subreddit="privacy",
        title="Protect your financial accounts",
        snippet="How to keep your personal data private."
    )
    passes, code, reason = scout_ranking_engine.apply_hard_gates(bad_cand, req)
    assert not passes
    assert code == ScoutFailureCode.SOURCE_SCOPE_MISMATCH
    assert "r/privacy" in reason


def test_hard_gate_reddit_url_structure():
    """Reddit search must point to /comments/<id>, not generic subreddits or search pages."""
    req = ScoutSourceRequest(query="Nvidia earnings", platform_hint="reddit")
    bad_url_cand = CandidateSource(
        url="https://www.reddit.com/r/stocks/",
        canonical_url="https://www.reddit.com/r/stocks/",
        platform="reddit",
        source_type="subreddit",
        external_id="stocks",
        subreddit="stocks",
        title="r/stocks homepage"
    )
    passes, code, _ = scout_ranking_engine.apply_hard_gates(bad_url_cand, req)
    assert not passes
    assert code == ScoutFailureCode.INVALID_URL_STRUCTURE


def test_hard_gate_twitter_reserved_path():
    """X search must not match settings, home, or explore pages."""
    req = ScoutSourceRequest(query="Elon Musk", platform_hint="twitter")
    bad_cand = CandidateSource(
        url="https://x.com/explore",
        canonical_url="https://x.com/explore",
        platform="twitter",
        source_type="status",
        external_id="explore",
        title="Explore / X"
    )
    passes, code, _ = scout_ranking_engine.apply_hard_gates(bad_cand, req)
    assert not passes
    assert code == ScoutFailureCode.INVALID_URL_STRUCTURE


# ─────────────────────────────────────────────────────────────────────────────
# 2. ANTI-TOKEN-CHEAT TESTS
# ─────────────────────────────────────────────────────────────────────────────

def test_anti_token_cheat_satya_nadella():
    """Single token 'Satya' (e.g. Satya incense on r/Incense) must be REJECTED without Microsoft context."""
    req = ScoutSourceRequest(query="CEO speech", target_entity="Satya Nadella")
    cand = CandidateSource(
        url="https://www.reddit.com/r/Incense/comments/123/best_satya_nag_champa/",
        canonical_url="https://www.reddit.com/r/Incense/comments/123/best_satya_nag_champa/",
        platform="reddit",
        source_type="post",
        external_id="123",
        title="Best Satya Nag Champa aromas",
        snippet="Discussion of Indian Satya incense sticks."
    )
    passes, code, _ = scout_ranking_engine.apply_hard_gates(cand, req)
    assert not passes
    assert code == ScoutFailureCode.TOKEN_CHEAT_REJECTED


def test_anti_token_cheat_sam_altman():
    """'Sam' in Lord of the Rings must be REJECTED for 'Sam Altman'."""
    req = ScoutSourceRequest(query="OpenAI founder", target_entity="Sam Altman")
    cand = CandidateSource(
        url="https://www.reddit.com/r/lotr/comments/456/samwise_gamgee_hero/",
        canonical_url="https://www.reddit.com/r/lotr/comments/456/samwise_gamgee_hero/",
        platform="reddit",
        source_type="post",
        external_id="456",
        title="Why Sam is the true hero of Lord of the Rings",
        snippet="Sam bravely carried Frodo up Mount Doom."
    )
    passes, code, _ = scout_ranking_engine.apply_hard_gates(cand, req)
    assert not passes
    assert code == ScoutFailureCode.TOKEN_CHEAT_REJECTED


def test_anti_token_cheat_jensen_huang():
    """'Jensen' in gaming must be REJECTED for 'Jensen Huang'."""
    req = ScoutSourceRequest(query="GPU architecture", target_entity="Jensen Huang")
    cand = CandidateSource(
        url="https://www.reddit.com/r/leagueoflegends/comments/789/c9_jensen_mid_lane/",
        canonical_url="https://www.reddit.com/r/leagueoflegends/comments/789/c9_jensen_mid_lane/",
        platform="reddit",
        source_type="post",
        external_id="789",
        title="C9 Jensen outstanding mid lane performance",
        snippet="Jensen played Orianna in the playoffs."
    )
    passes, code, _ = scout_ranking_engine.apply_hard_gates(cand, req)
    assert not passes
    assert code == ScoutFailureCode.TOKEN_CHEAT_REJECTED


# ─────────────────────────────────────────────────────────────────────────────
# 3. FINANCIAL NUMBER EXTRACTION TESTS
# ─────────────────────────────────────────────────────────────────────────────

def test_financial_number_extraction_multicurrency():
    text = (
        "Nvidia reported record Q4 revenue of $5.4B, up 22% YoY. "
        "Operating margin expanded 200 bps to 45.2%. "
        "Diluted earnings were $1.25 EPS. "
        "Tata Motors disclosed quarterly profit of ₹10,000 crore while capex is projected at $12B."
    )
    facts = financial_number_extractor.extract_facts(text)
    assert len(facts) >= 4

    rev_fact = next((f for f in facts if f.metric == "revenue"), None)
    assert rev_fact is not None
    assert rev_fact.normalized_value == 5_400_000_000.0
    assert rev_fact.currency == "USD"
    assert rev_fact.unit == "billion" or rev_fact.unit == "b"

    inr_fact = next((f for f in facts if f.currency == "INR"), None)
    assert inr_fact is not None
    assert inr_fact.normalized_value == 100_000_000_000.0  # 10,000 * 10,000,000

    eps_fact = next((f for f in facts if f.metric == "eps"), None)
    assert eps_fact is not None
    assert eps_fact.normalized_value == 1.25


# ─────────────────────────────────────────────────────────────────────────────
# 4. CORPORATE EVENT EXTRACTION TESTS
# ─────────────────────────────────────────────────────────────────────────────

def test_corporate_event_extraction():
    text = (
        "Apple unveiled new M4 Mac chips during its launch event. "
        "Separately, Pfizer announced an agreement to acquire Biotech Corp for $2.8B. "
        "Boeing management raised full-year guidance after commercial delivery surge."
    )
    events = corporate_event_extractor.extract_events(text, company_name="Pfizer", ticker="PFE")
    assert len(events) >= 2

    m_and_a = next((e for e in events if e.event_type == CorporateEventType.M_AND_A), None)
    assert m_and_a is not None
    assert "acquire" in m_and_a.description.lower()

    guidance = next((e for e in events if e.event_type == CorporateEventType.GUIDANCE_CHANGE), None)
    assert guidance is not None
    assert guidance.direction == FactDirection.POSITIVE


# ─────────────────────────────────────────────────────────────────────────────
# 5. TEMPORAL DISAMBIGUATION TESTS
# ─────────────────────────────────────────────────────────────────────────────

def test_temporal_disambiguation():
    text = "The merger was announced on January 15, 2026 before markets opened."
    pub = "2026-01-16T10:00:00Z"
    pub_iso, event_iso = temporal_extractor.disambiguate(pub, text)

    assert "2026-01-16" in pub_iso
    assert event_iso is not None
    assert "2026-01-15" in event_iso


# ─────────────────────────────────────────────────────────────────────────────
# 6. DEDUPLICATION & WIRE SYNDICATION CLUSTERING TESTS
# ─────────────────────────────────────────────────────────────────────────────

def test_syndication_and_story_clustering():
    items = [
        ScoutEvidence(
            evidence_id="src_1",
            url="https://www.reuters.com/business/tech/amd-mi350-chips-2026-02-10/",
            canonical_url="https://www.reuters.com/business/tech/amd-mi350-chips-2026-02-10/",
            platform="news",
            source_type="article",
            source_tier=SourceTier.TIER_2_PRESS.value,
            external_id="reuters_1",
            title="AMD announces MI350 accelerator ramp for datacenter hyperscalers",
            author="Reuters Tech",
            body="AMD announced the ramp of its MI350 AI accelerators for hyperscalers.",
            snippet="AMD MI350 ramp announced.",
            published_at="2026-02-10T08:00:00Z",
            event_at=None,
            retrieved_at="2026-02-10T08:05:00Z",
            is_primary=False
        ),
        ScoutEvidence(
            evidence_id="src_2",
            url="https://finance.yahoo.com/news/amd-announces-mi350-accelerator-ramp-reuters-080512.html",
            canonical_url="https://finance.yahoo.com/news/amd-announces-mi350-accelerator-ramp-reuters-080512.html",
            platform="news",
            source_type="article",
            source_tier=SourceTier.TIER_5_AGGREGATE.value,
            external_id="yahoo_1",
            title="AMD announces MI350 accelerator ramp for datacenter hyperscalers (Reuters)",
            author="Yahoo Finance",
            body="Reuters - AMD announced the ramp of its MI350 AI accelerators for hyperscalers.",
            snippet="AMD MI350 ramp via Reuters.",
            published_at="2026-02-10T08:05:00Z",
            event_at=None,
            retrieved_at="2026-02-10T08:06:00Z",
            is_primary=False
        )
    ]

    deduped, clusters = scout_deduplicator.cluster_evidence(items)
    assert len(clusters) == 1
    cluster = clusters[0]
    assert cluster.cluster_id == "cluster_001"
    # Second item should be detected as syndicated echo
    assert items[1].syndicated_from == "reuters"


# ─────────────────────────────────────────────────────────────────────────────
# 7. CONTRADICTION DETECTION TESTS
# ─────────────────────────────────────────────────────────────────────────────

def test_contradiction_detection_conflicting_deal_values():
    """Deal values of $2.0B vs $3.5B must trigger explicit contradiction without averaging."""
    from backend.services.agent_reach.scout.models import FinancialFact

    ev_a = ScoutEvidence(
        evidence_id="ev_a",
        url="https://wsj.com/deal",
        canonical_url="https://wsj.com/deal",
        platform="news",
        source_type="article",
        source_tier=SourceTier.TIER_2_PRESS.value,
        external_id="wsj",
        title="WSJ Deal Report",
        author="Wall Street Journal",
        body="Deal valued at $2.0B.",
        snippet="Deal valued at $2.0B.",
        published_at="2026-03-01T10:00:00Z",
        event_at=None,
        retrieved_at="2026-03-01T10:05:00Z",
        financial_facts=[FinancialFact(
            metric="deal_value",
            raw_value="$2.0B",
            normalized_value=2_000_000_000.0,
            unit="billion",
            currency="USD",
            period="2026",
            context_sentence="Acquisition agreement valued at $2.0B."
        )]
    )

    ev_b = ScoutEvidence(
        evidence_id="ev_b",
        url="https://bloomberg.com/deal",
        canonical_url="https://bloomberg.com/deal",
        platform="news",
        source_type="article",
        source_tier=SourceTier.TIER_2_PRESS.value,
        external_id="bloomberg",
        title="Bloomberg Deal Scoop",
        author="Bloomberg News",
        body="Deal valued at $3.5B according to sources.",
        snippet="Deal valued at $3.5B.",
        published_at="2026-03-01T10:02:00Z",
        event_at=None,
        retrieved_at="2026-03-01T10:05:00Z",
        financial_facts=[FinancialFact(
            metric="deal_value",
            raw_value="$3.5B",
            normalized_value=3_500_000_000.0,
            unit="billion",
            currency="USD",
            period="2026",
            context_sentence="People familiar stated the transaction is valued at $3.5B."
        )]
    )

    _, clusters = scout_deduplicator.cluster_evidence([ev_a, ev_b])
    contradictions = scout_corroboration_engine.analyze_corroboration([ev_a, ev_b], clusters)

    assert len(contradictions) >= 1
    assert "$2.0B" in contradictions[0].discrepancy_description
    assert "$3.5B" in contradictions[0].discrepancy_description
    assert clusters[0].epistemic_status == EpistemicStatus.CONTRADICTED


# ─────────────────────────────────────────────────────────────────────────────
# 8. THE TEN CANONICAL AUDIT REGRESSION TRAPS
# ─────────────────────────────────────────────────────────────────────────────

def test_trap_1_reddit_investing_vs_privacy():
    req = ScoutSourceRequest(query="Index funds", requested_scope="r/investing")
    cand = CandidateSource(
        url="https://reddit.com/r/privacy/comments/1/vpn/",
        canonical_url="https://reddit.com/r/privacy/comments/1/vpn/",
        platform="reddit",
        source_type="post",
        external_id="1",
        subreddit="privacy",
        title="VPN usage"
    )
    passes, code, _ = scout_ranking_engine.apply_hard_gates(cand, req)
    assert not passes
    assert code == ScoutFailureCode.SOURCE_SCOPE_MISMATCH


def test_trap_2_satya_nadella_vs_incense():
    req = ScoutSourceRequest(query="Cloud AI strategy", target_entity="Satya Nadella")
    cand = CandidateSource(
        url="https://reddit.com/r/Incense/comments/2/satya/",
        canonical_url="https://reddit.com/r/Incense/comments/2/satya/",
        platform="reddit",
        source_type="post",
        external_id="2",
        title="Satya Sai Baba incense reviews"
    )
    passes, code, _ = scout_ranking_engine.apply_hard_gates(cand, req)
    assert not passes
    assert code == ScoutFailureCode.TOKEN_CHEAT_REJECTED


def test_trap_3_sam_altman_vs_samwise():
    req = ScoutSourceRequest(query="AGI timeline", target_entity="Sam Altman")
    cand = CandidateSource(
        url="https://reddit.com/r/lotr/comments/3/samwise/",
        canonical_url="https://reddit.com/r/lotr/comments/3/samwise/",
        platform="reddit",
        source_type="post",
        external_id="3",
        title="Sam's loyalty to Frodo"
    )
    passes, code, _ = scout_ranking_engine.apply_hard_gates(cand, req)
    assert not passes
    assert code == ScoutFailureCode.TOKEN_CHEAT_REJECTED


def test_trap_4_jensen_huang_vs_unrelated_jensen():
    req = ScoutSourceRequest(query="Blackwell servers", target_entity="Jensen Huang")
    cand = CandidateSource(
        url="https://reddit.com/r/leagueoflegends/comments/4/jensen/",
        canonical_url="https://reddit.com/r/leagueoflegends/comments/4/jensen/",
        platform="reddit",
        source_type="post",
        external_id="4",
        title="Jensen signs with new esports team"
    )
    passes, code, _ = scout_ranking_engine.apply_hard_gates(cand, req)
    assert not passes
    assert code == ScoutFailureCode.TOKEN_CHEAT_REJECTED


def test_trap_5_corporate_domain_on_social_request():
    req = ScoutSourceRequest(query="Community sentiment", platform_hint="reddit")
    cand = CandidateSource(
        url="https://www.amd.com/en/products/processors",
        canonical_url="https://www.amd.com/en/products/processors",
        platform="reddit",
        source_type="post",
        external_id="amd",
        title="AMD Official Product Page"
    )
    passes, code, _ = scout_ranking_engine.apply_hard_gates(cand, req)
    assert not passes
    assert code == ScoutFailureCode.DOMAIN_REJECTED


def test_trap_6_ai_datacenter_electricity_vs_generic_chatgpt():
    """Generic ChatGPT post without electricity/energy terms should receive low score."""
    req = ScoutSourceRequest(query="AI data center electricity consumption", target_entity="datacenter power")
    cand_offtopic = CandidateSource(
        url="https://reddit.com/r/ChatGPT/comments/101/funny_chatgpt_joke/",
        canonical_url="https://reddit.com/r/ChatGPT/comments/101/funny_chatgpt_joke/",
        platform="reddit",
        source_type="post",
        external_id="101",
        title="Funny ChatGPT conversation with my cat",
        snippet="ChatGPT told a hilarious bedtime story."
    )
    cand_ontopic = CandidateSource(
        url="https://reddit.com/r/energy/comments/102/ai_datacenters_grid_power/",
        canonical_url="https://reddit.com/r/energy/comments/102/ai_datacenters_grid_power/",
        platform="reddit",
        source_type="post",
        external_id="102",
        title="AI data centers surge electricity grid demands",
        snippet="Hyperscale datacenters require gigawatts of nuclear and gas capacity."
    )
    score_off = scout_ranking_engine._compute_score(cand_offtopic, req)
    score_on = scout_ranking_engine._compute_score(cand_ontopic, req)
    assert score_on > score_off


def test_trap_7_nvidia_blackwell_vs_unrelated_nvidia_tweet():
    """Requested Blackwell specifically; candidate about older GeForce gaming gets ranked below Blackwell."""
    req = ScoutSourceRequest(query="Nvidia Blackwell B200 GB200 architecture", target_entity="Nvidia", tickers=["NVDA"])
    cand_blackwell = CandidateSource(
        url="https://x.com/tech/status/201",
        canonical_url="https://x.com/tech/status/201",
        platform="twitter",
        source_type="status",
        external_id="201",
        title="Nvidia Blackwell B200 server racks shipped",
        snippet="GB200 NVL72 liquid-cooled supercomputers rolling out."
    )
    cand_geforce = CandidateSource(
        url="https://x.com/gamer/status/202",
        canonical_url="https://x.com/gamer/status/202",
        platform="twitter",
        source_type="status",
        external_id="202",
        title="Nvidia GeForce RTX 3060 driver update",
        snippet="Fixed minor stuttering in CS:GO."
    )
    score_bw = scout_ranking_engine._compute_score(cand_blackwell, req)
    score_gf = scout_ranking_engine._compute_score(cand_geforce, req)
    assert score_bw > score_gf


def test_trap_8_chips_act_vs_generic_act():
    """CHIPS Act query should rank semiconductor legislation above generic Broadway act."""
    req = ScoutSourceRequest(query="CHIPS and Science Act semiconductor subsidies", target_entity="CHIPS Act")
    cand_act = CandidateSource(
        url="https://reddit.com/r/broadway/comments/301/third_act_musical/",
        canonical_url="https://reddit.com/r/broadway/comments/301/third_act_musical/",
        platform="reddit",
        source_type="post",
        external_id="301",
        title="Third act of musical theatre was stunning",
        snippet="The opening act and closing act were great."
    )
    passes, code, _ = scout_ranking_engine.apply_hard_gates(cand_act, req)
    assert not passes
    assert code == ScoutFailureCode.TOKEN_CHEAT_REJECTED


def test_trap_9_space_data_center_vs_space_meme():
    """Space data centers query should prioritize orbital compute over Kerbal space meme."""
    req = ScoutSourceRequest(query="space-based orbital data centers compute", target_entity="orbital data center")
    cand_meme = CandidateSource(
        url="https://reddit.com/r/gaming/comments/401/kerbal_space_station/",
        canonical_url="https://reddit.com/r/gaming/comments/401/kerbal_space_station/",
        platform="reddit",
        source_type="post",
        external_id="401",
        title="Kerbal Space Program funny crash",
        snippet="My rocket failed to reach orbital space."
    )
    passes, code, _ = scout_ranking_engine.apply_hard_gates(cand_meme, req)
    assert not passes
    assert code == ScoutFailureCode.TOKEN_CHEAT_REJECTED


def test_trap_10_california_sb1047_vs_generic_california():
    """California SB 1047 AI bill query should reject generic California travel or housing posts."""
    req = ScoutSourceRequest(query="California SB 1047 frontier AI safety bill", target_entity="SB 1047")
    cand_travel = CandidateSource(
        url="https://reddit.com/r/travel/comments/501/california_roadtrip/",
        canonical_url="https://reddit.com/r/travel/comments/501/california_roadtrip/",
        platform="reddit",
        source_type="post",
        external_id="501",
        title="Best roadtrip route in Southern California",
        snippet="Driving down Highway 1 along the coast of California."
    )
    passes, code, _ = scout_ranking_engine.apply_hard_gates(cand_travel, req)
    assert not passes
    assert code == ScoutFailureCode.TOKEN_CHEAT_REJECTED


# ─────────────────────────────────────────────────────────────────────────────
# 9. END-TO-END SCOUT ENGINE INTEGRATION & TELEMETRY
# ─────────────────────────────────────────────────────────────────────────────

def test_scout_engine_mocked_acquisition():
    """Verify that ScoutSourceEngine processes a request and returns typed ScoutResult."""
    req = ScoutSourceRequest(
        query="Tata Motors financial results",
        target_entity="Tata Motors",
        tickers=["TATAMOTORS.NS"],
        max_candidates=3
    )
    res = scout_source_engine.execute(req)

    assert res.query == req.query
    assert res.entity == "Tata Motors"
    assert "total_latency_ms" in res.telemetry
    assert "candidates_discovered" in res.telemetry


def test_scout_agent_acquire_market_intelligence():
    """Verify that ScoutAgent direct acquire_market_intelligence method works."""
    from backend.agents.scout_agent import ScoutAgent
    agent = ScoutAgent()
    intel = agent.acquire_market_intelligence(ticker="TATAMOTORS.NS", max_candidates=2)

    assert intel["ticker"] == "TATAMOTORS.NS"
    assert "epistemic_status" in intel
    assert "financial_facts" in intel
    assert "events" in intel
    assert "clusters" in intel
    assert "telemetry" in intel

