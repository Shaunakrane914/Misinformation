"""
Aegis Protocol — Trending Temporal Relevance & Freshness Adversarial Test Suite
================================================================================
Comprehensive adversarial tests verifying:
1. Recent relevant story is accepted.
2. 2021 story fetched today remains stale.
3. Syndicated old story with fresh mirror timestamp remains stale.
4. Recent update to old article follows explicit update policy.
5. Missing/unparseable publication timestamp handled conservatively.
6. Future-dated timestamp cannot gain artificial recency advantage.
7. Timezone invariance (+08:00 vs UTC vs -05:00).
8. Irrelevant recent competitor story is not accepted merely for being fresh.
9. Neural reranker cannot restore candidate rejected by temporal gate.
10. Other three agents (BrandShield, Scout, Personal Watch) retain existing behavior.
"""

from datetime import datetime, timezone, timedelta
import pytest

from backend.services.research.temporal_guard import TemporalGuard, temporal_guard, TemporalAssessment
from backend.services.research.relevance_gate import RelevanceGate, relevance_gate
from backend.services.research.candidate_ranker import CandidateRanker, candidate_ranker
from backend.services.research.semantic_reranker import SemanticReranker
from backend.services.research.research_models import EvidenceItem


# Fixed reference time for deterministic testing: 2026-10-09 12:00:00 UTC
REF_TIME = datetime(2026, 10, 9, 12, 0, 0, tzinfo=timezone.utc)


def test_1_recent_relevant_microsoft_story_accepted():
    """1. A recent, genuinely relevant Microsoft story is eligible and accepted."""
    cand = {
        "id": "cand_recent_msft",
        "title": "Microsoft Copilot Enterprise Adoption Surges in New Survey",
        "snippet": "New telemetry shows enterprise adoption of Microsoft 365 Copilot grew 45% this month.",
        "url": "https://techwire.com/news/microsoft-copilot-surge",
        "published_at": (REF_TIME - timedelta(hours=3)).isoformat(),
        "discovered_at": REF_TIME.isoformat(),
    }

    # TemporalGuard evaluation
    assessment = temporal_guard.evaluate(cand, reference_time=REF_TIME, window_hours=48.0)
    assert assessment.is_eligible is True
    assert assessment.status == "FRESH"
    assert assessment.age_hours == pytest.approx(3.0, abs=0.1)
    assert assessment.recency_score > 0.90
    assert assessment.rejection_reason is None

    # Full RelevanceGate evaluation for Trending domain
    rel_assess = relevance_gate.evaluate_item(
        cand,
        target_entity="Microsoft",
        domain="trending",
        intent="viral trending discussion",
        reference_time=REF_TIME,
        window_hours=48.0,
    )
    assert rel_assess.is_accepted is True
    assert rel_assess.rejection_stage is None
    assert rel_assess.temporal_status == "FRESH"


def test_2_historical_2021_story_fetched_today_remains_stale():
    """2. A 2021 Microsoft story fetched today remains stale."""
    cand = {
        "id": "cand_2021_stale",
        "title": "Microsoft Announces Windows 11 Official Rollout Schedule",
        "snippet": "Microsoft today unveiled the worldwide release timeline for Windows 11.",
        "url": "https://techportal.com/2021/04/msft-windows-11",
        "published_at": "2021-04-10T12:00:00Z",
        "discovered_at": REF_TIME.isoformat(),  # Fetched today
        "retrieved_at": REF_TIME.isoformat(),
    }

    assessment = temporal_guard.evaluate(cand, reference_time=REF_TIME, window_hours=48.0)
    assert assessment.is_eligible is False
    assert assessment.status == "STALE"
    assert assessment.age_hours > 40000.0
    assert "TEMPORAL_STALE" in assessment.rejection_reason
    assert assessment.context_only is True

    # Gate verification
    rel_assess = relevance_gate.evaluate_item(
        cand,
        target_entity="Microsoft",
        domain="trending",
        intent="viral trending discussion",
        reference_time=REF_TIME,
        window_hours=48.0,
    )
    assert rel_assess.is_accepted is False
    assert rel_assess.rejection_stage == "TEMPORAL_GATE_ERROR"
    assert "TEMPORAL_STALE" in rel_assess.rejection_reason


def test_3_syndicated_old_story_with_fresh_mirror_timestamp():
    """3. A syndicated old story with a fresh mirror timestamp remains stale."""
    cand = {
        "id": "cand_syndicated_mirror",
        "title": "Syndicated Mirror: Archived 2021 Report: Microsoft Announces Earlier Generation OS",
        "snippet": "Syndicated wire copy covering Archived 2021 Report: Microsoft Announces Earlier Generation OS.",
        "url": "https://wire-mirror.com/republished/msft-os",
        "published_at": (REF_TIME - timedelta(hours=2)).isoformat(),  # Mirror published 2 hours ago
        "discovered_at": REF_TIME.isoformat(),
    }

    assessment = temporal_guard.evaluate(cand, reference_time=REF_TIME, window_hours=48.0)
    assert assessment.is_eligible is False
    assert assessment.status == "SYNDICATED_STALE"
    assert "TEMPORAL_SYNDICATED_STALE" in assessment.rejection_reason

    rel_assess = relevance_gate.evaluate_item(
        cand,
        target_entity="Microsoft",
        domain="trending",
        intent="viral trending discussion",
        reference_time=REF_TIME,
        window_hours=48.0,
    )
    assert rel_assess.is_accepted is False
    assert rel_assess.rejection_stage == "TEMPORAL_GATE_ERROR"


def test_4_recent_update_to_old_article_follows_update_policy():
    """4. A recent update to an old article follows the explicitly defined update policy."""
    cand = {
        "id": "cand_updated_story",
        "title": "Microsoft Enterprise Cloud Licensing Framework",
        "snippet": "Overview of enterprise licensing terms and support lifecycle.",
        "url": "https://techguide.com/msft-licensing",
        "published_at": "2021-06-15T09:00:00Z",  # 5 years old
        "updated_at": (REF_TIME - timedelta(hours=2)).isoformat(),  # Updated 2h ago
        "discovered_at": REF_TIME.isoformat(),
    }

    # Policy A: Default Trending policy (allow_updated=False) rejects active trend
    assess_strict = temporal_guard.evaluate(
        cand, reference_time=REF_TIME, window_hours=48.0, allow_updated=False
    )
    assert assess_strict.is_eligible is False
    assert assess_strict.status == "UPDATED_HISTORICAL_REJECTED"
    assert "TEMPORAL_STALE_HISTORICAL_UPDATE" in assess_strict.rejection_reason
    assert assess_strict.context_only is True

    # Policy B: allow_updated=True accepts with explicit tracking
    assess_allow = temporal_guard.evaluate(
        cand, reference_time=REF_TIME, window_hours=48.0, allow_updated=True
    )
    assert assess_allow.is_eligible is True
    assert assess_allow.status == "UPDATED_HISTORICAL_ACCEPTED"
    assert assess_allow.details.get("is_update") is True
    assert assess_allow.details.get("original_age_hours") > 40000.0


def test_5_missing_publication_timestamp_handled_conservatively():
    """5. Missing or unparseable publication timestamp is handled conservatively and transparently."""
    cand_missing = {
        "id": "cand_missing_ts",
        "title": "Microsoft Rumored To Be Developing Quantum Computing Core",
        "snippet": "Unconfirmed forum leaks regarding Microsoft quantum architecture.",
        "url": "https://leakforum.net/msft-quantum",
        "published_at": "",  # Empty timestamp
        "discovered_at": REF_TIME.isoformat(),
    }
    cand_none = {
        "id": "cand_none_ts",
        "title": "Microsoft Rumored To Be Developing Quantum Computing Core",
        "snippet": "Unconfirmed forum leaks regarding Microsoft quantum architecture.",
        "url": "https://leakforum.net/msft-quantum",
        "published_at": None,
        "discovered_at": REF_TIME.isoformat(),
    }
    cand_garbage = {
        "id": "cand_garbage_ts",
        "title": "Microsoft Rumored To Be Developing Quantum Computing Core",
        "snippet": "Unconfirmed forum leaks regarding Microsoft quantum architecture.",
        "url": "https://leakforum.net/msft-quantum",
        "published_at": "InvalidTimestampString123!@#",
        "discovered_at": REF_TIME.isoformat(),
    }

    for c in [cand_missing, cand_none, cand_garbage]:
        assess = temporal_guard.evaluate(c, reference_time=REF_TIME, window_hours=48.0)
        assert assess.is_eligible is False
        assert assess.status == "MISSING_TIMESTAMP"
        assert "TEMPORAL_MISSING_TIMESTAMP" in assess.rejection_reason
        assert assess.recency_score <= 0.05

        rel = relevance_gate.evaluate_item(
            c, target_entity="Microsoft", domain="trending", reference_time=REF_TIME
        )
        assert rel.is_accepted is False
        assert rel.rejection_stage == "TEMPORAL_GATE_ERROR"


def test_6_future_dated_timestamp_cannot_gain_recency_advantage():
    """6. A future-dated timestamp cannot gain an artificial recency advantage."""
    cand_future = {
        "id": "cand_future_ts",
        "title": "Microsoft Keynote Announcement Highlights",
        "snippet": "Transcript of executive keynote speech.",
        "url": "https://futurenews.com/msft-keynote",
        "published_at": (REF_TIME + timedelta(days=7)).isoformat(),  # 7 days in future
        "discovered_at": REF_TIME.isoformat(),
    }

    assess = temporal_guard.evaluate(cand_future, reference_time=REF_TIME, window_hours=48.0)
    assert assess.is_eligible is False
    assert assess.status == "FUTURE_DATED"
    assert assess.recency_score == 0.0
    assert "TEMPORAL_FUTURE_DATED" in assess.rejection_reason

    rel = relevance_gate.evaluate_item(
        cand_future, target_entity="Microsoft", domain="trending", reference_time=REF_TIME
    )
    assert rel.is_accepted is False
    assert rel.rejection_stage == "TEMPORAL_GATE_ERROR"


def test_7_timezone_invariance():
    """7. Timezone differences do not change eligibility."""
    # 2 hours before REF_TIME expressed in different timezones:
    target_utc_dt = REF_TIME - timedelta(hours=2)

    # 1. UTC format
    ts_utc = target_utc_dt.isoformat()
    # 2. Beijing offset (+08:00)
    ts_beijing = (target_utc_dt.astimezone(timezone(timedelta(hours=8)))).isoformat()
    # 3. New York offset (-04:00)
    ts_ny = (target_utc_dt.astimezone(timezone(timedelta(hours=-4)))).isoformat()
    # 4. RFC 2822 format
    ts_rfc = "Fri, 09 Oct 2026 10:00:00 GMT"

    for ts in [ts_utc, ts_beijing, ts_ny, ts_rfc]:
        cand = {
            "id": "cand_tz",
            "title": "Microsoft Azure Expansion in Global Regions",
            "snippet": "Infrastructure rollout across datacenter hubs.",
            "url": "https://azure.microsoft.com/updates",
            "published_at": ts,
            "discovered_at": REF_TIME.isoformat(),
        }
        assess = temporal_guard.evaluate(cand, reference_time=REF_TIME, window_hours=48.0)
        assert assess.is_eligible is True
        assert assess.status == "FRESH"
        assert assess.age_hours == pytest.approx(2.0, abs=0.1)


def test_8_irrelevant_recent_competitor_story_rejected():
    """8. An irrelevant recent competitor story is not accepted merely for being fresh."""
    cand = {
        "id": "cand_competitor_recent",
        "title": "Sony Announces New DualSense Wireless Controller Colorways for PlayStation 5",
        "snippet": "Sony Interactive Entertainment today announced three new vibrant controller editions for PS5 players.",
        "url": "https://playstation.blog/controller-updates",
        "published_at": (REF_TIME - timedelta(hours=1)).isoformat(),  # Very fresh!
        "discovered_at": REF_TIME.isoformat(),
    }

    # TemporalGuard alone sees it as fresh
    temp_assess = temporal_guard.evaluate(cand, reference_time=REF_TIME, window_hours=48.0)
    assert temp_assess.is_eligible is True
    assert temp_assess.status == "FRESH"

    # But RelevanceGate evaluates Microsoft and MUST reject it on entity grounds
    rel_assess = relevance_gate.evaluate_item(
        cand,
        target_entity="Microsoft",
        domain="trending",
        intent="viral trending discussion",
        reference_time=REF_TIME,
    )
    assert rel_assess.is_accepted is False
    assert rel_assess.rejection_stage in ("HARD_GATE_ERROR", "ENTITY_RESOLUTION_ERROR")
    assert rel_assess.entity_score < 0.35


def test_9_neural_reranker_cannot_restore_temporally_rejected_candidate():
    """9. The neural reranker cannot restore a candidate rejected by the temporal gate."""
    stale_cand = {
        "candidate_id": "cand_stale_high_semantic",
        "title": "Microsoft Copilot Full Feature Architecture Documentation and Guidelines",
        "snippet": "Complete official reference guide to Microsoft Copilot enterprise integrations.",
        "published_at": "2021-04-10T12:00:00Z",
        "temporal_eligible": False,  # Rejected by temporal gate
        "rejection_stage": "TEMPORAL_GATE_ERROR",
        "relevance_score": 0.0,
        "first_stage_score": 0.0,
        "entity_score": 0.95,
    }

    fresh_cand = {
        "candidate_id": "cand_fresh_moderate_semantic",
        "title": "Microsoft Trending Discussion: Community Reactions to Feature Preview",
        "snippet": "Social conversation and developer feedback on new Microsoft preview.",
        "published_at": (REF_TIME - timedelta(hours=4)).isoformat(),
        "temporal_eligible": True,
        "relevance_score": 0.70,
        "first_stage_score": 0.70,
        "entity_score": 0.90,
    }

    reranker = SemanticReranker(enabled=True)
    query = "Microsoft viral trending discussion"

    reranked = reranker.rerank(query, [stale_cand, fresh_cand], top_k=2)

    # Invariant: Temporally ineligible candidate receives rerank_score 0.0 and cannot rank first
    assert reranked[0]["candidate_id"] == "cand_fresh_moderate_semantic"
    stale_res = next(c for c in reranked if c["candidate_id"] == "cand_stale_high_semantic")
    assert stale_res["rerank_score"] == 0.0


def test_10_other_three_agents_retain_existing_behavior():
    """10. Other three agents (BrandShield, Scout, Personal Watch) retain existing behavior."""
    historical_brand_cand = {
        "id": "cand_historical_brand",
        "title": "Analysis of Past Microsoft Trademark Phishing Domain 'msft-login-support.com'",
        "snippet": "Technical post-mortem examining rogue domain impersonating Microsoft corporate portals in 2021.",
        "url": "https://threatintel.net/msft-login-phishing-2021",
        "published_at": "2021-05-12T10:00:00Z",
        "discovered_at": REF_TIME.isoformat(),
    }

    historical_scout_cand = {
        "id": "cand_historical_scout",
        "title": "Microsoft Corporation FY2021 Annual Report Form 10-K SEC Filing",
        "snippet": "United States Securities and Exchange Commission annual report for fiscal year ended June 30, 2021.",
        "url": "https://sec.gov/edgar/data/789019/msft-10k-2021",
        "published_at": "2021-07-30T16:00:00Z",
        "discovered_at": REF_TIME.isoformat(),
    }

    historical_personal_cand = {
        "id": "cand_historical_personal",
        "title": "Satya Nadella 2021 Commencement Address at University",
        "snippet": "Transcript of Microsoft CEO Satya Nadella addressing graduates on technology leadership.",
        "url": "https://university.edu/speeches/satya-nadella-2021",
        "published_at": "2021-06-01T14:00:00Z",
        "discovered_at": REF_TIME.isoformat(),
    }

    # BrandShield (domain='brand') must accept historical threat intelligence
    rel_brand = relevance_gate.evaluate_item(
        historical_brand_cand, target_entity="Microsoft", domain="brand", intent="trademark infringement fake"
    )
    assert rel_brand.is_accepted is True
    assert rel_brand.rejection_stage is None

    # Scout (domain='financial') must accept historical 10-K filings
    rel_scout = relevance_gate.evaluate_item(
        historical_scout_cand, target_entity="Microsoft", domain="financial", intent="sec 10-k earnings report"
    )
    assert rel_scout.is_accepted is True
    assert rel_scout.rejection_stage is None

    # Personal Watch (domain='personal') must accept historical executive profile
    rel_personal = relevance_gate.evaluate_item(
        historical_personal_cand, target_entity="Satya Nadella", domain="personal", intent="executive public statements"
    )
    assert rel_personal.is_accepted is True
    assert rel_personal.rejection_stage is None
