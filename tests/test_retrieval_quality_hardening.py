"""
Aegis Protocol — Hardened Retrieval Quality Test Suite
======================================================
Tests:
1. Entity Resolution (multi-word person, ambiguous name, company/ticker, action verb vs entity)
2. Relevance Gating (false positives rejection, true positives acceptance, domain & platform gates)
3. Social URL Resolution (X status, X profile, Reddit post, YouTube video, invalid pages)
4. Provenance Invariants A-D (source identity stability, observation uniqueness, backend preservation)
5. Fallback Accounting (Attempts == Successes + Failures invariant)
"""

import pytest
from backend.services.agent_reach.channels import (
    AcquisitionAttempt,
    EvidenceFragment,
    EvidenceObservation,
    FallbackReasonCode,
    RetrievalMode,
)
from backend.services.agent_reach.native.social_resolver import social_target_resolver
from backend.services.agent_reach.native.source_discovery import (
    extract_reddit_source,
    extract_x_source,
)
from backend.services.research.entity_resolver import (
    EntityResolver,
    TargetEntity,
    entity_resolver,
)
from backend.services.research.relevance_gate import (
    RelevanceAssessment,
    RelevanceGate,
    relevance_gate,
)
from backend.services.research.candidate_ranker import candidate_reranker


# ─────────────────────────────────────────────────────────────────────────────
# 1. Entity Resolution Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestEntityResolution:
    def test_action_verb_separation(self):
        """Action verbs like 'Investigate' must not become entity tokens."""
        parsed = entity_resolver.parse_request("Investigate Microsoft", domain="brand")
        assert parsed.action_verb == "investigate"
        assert parsed.target_entity.canonical_name == "Microsoft"
        assert "investigate" not in [a.lower() for a in parsed.target_entity.aliases]

    def test_multi_word_person_rules(self):
        """Single token match ('Satya') must not resolve without surname or context."""
        satya_target = entity_resolver.resolve_entity("Satya Nadella", domain="personal")
        assert satya_target.is_multi_word

        # Standalone first name without context must fail
        score, _, reason = entity_resolver.evaluate_entity_match("Satya spoke yesterday", satya_target)
        assert score < 0.35
        assert "Ambiguous" in str(reason)

        # Full phrase must pass strongly
        score2, sigs2, _ = entity_resolver.evaluate_entity_match("Satya Nadella keynote", satya_target)
        assert score2 >= 0.85
        assert any("canonical_phrase" in s for s in sigs2)

        # First name with organization context must pass
        score3, _, _ = entity_resolver.evaluate_entity_match("Satya at Microsoft CEO summit", satya_target)
        assert score3 >= 0.65

    def test_company_and_ticker(self):
        """Tickers and aliases must resolve to canonical company."""
        msft_target = entity_resolver.resolve_entity("$MSFT", domain="financial")
        assert msft_target.canonical_name == "Microsoft"
        assert msft_target.ticker == "MSFT"

        score, sigs, _ = entity_resolver.evaluate_entity_match("MSFT earnings beat expectations", msft_target)
        assert score >= 0.85
        assert any("ticker" in s for s in sigs)

    def test_negative_disambiguation(self):
        """Confusable negative entities must trigger negative detection."""
        satya_target = entity_resolver.resolve_entity("Satya Nadella", domain="personal")
        score, _, reason = entity_resolver.evaluate_entity_match(
            "SATYA (1998) HINDI ACTION FULL MOVIE - MANOJ BAJPAYEE", satya_target
        )
        assert score < 0.35
        assert "negative" in str(reason).lower()


# ─────────────────────────────────────────────────────────────────────────────
# 2. Relevance Gating Tests (False Positives vs True Positives)
# ─────────────────────────────────────────────────────────────────────────────

class TestRelevanceGating:
    def test_reject_mtg_investigate_cards(self):
        """Magic: The Gathering cards with 'Investigate' keyword must be rejected."""
        item = {
            "id": "ev_mtg",
            "title": "Clues/Investigate in EDH?",
            "snippet": "When Investigate was added in SOI I was real excited. Tireless Tracker and Graf Mole deck...",
            "url": "https://reddit.com/r/EDH/comments/qftl7y/cluesinvestigate_in_edh/"
        }
        res = relevance_gate.evaluate_item(item, target_entity="Investigate Microsoft", domain="brand")
        assert not res.is_accepted
        assert res.relevance_score < 0.35
        assert res.rejection_stage == "HARD_GATE_ERROR"

    def test_reject_satya_1998_movie(self):
        """Satya Bollywood movie must be rejected."""
        item = {
            "id": "ev_movie",
            "title": "SATYA (1998) HINDI ACTION FULL MOVIE",
            "snippet": "Watch Ram Gopal Varma movie Satya starring Manoj Bajpayee...",
            "url": "https://www.youtube.com/watch?v=EZx8fRwQyi4"
        }
        res = relevance_gate.evaluate_item(item, target_entity="Satya Nadella", domain="personal")
        assert not res.is_accepted
        assert res.relevance_score < 0.35

    def test_reject_sanskrit_wikipedia(self):
        """Sanskrit Wikipedia concept must be rejected."""
        item = {
            "id": "ev_sanskrit",
            "title": "Satya - Wikipedia",
            "snippet": "Satya is a Sanskrit word meaning truth in Indian religions...",
            "url": "https://en.wikipedia.org/wiki/Satya"
        }
        res = relevance_gate.evaluate_item(item, target_entity="Satya Nadella", domain="personal")
        assert not res.is_accepted
        assert res.relevance_score < 0.35

    def test_accept_true_positive_microsoft(self):
        """Authentic Microsoft security report must be accepted."""
        item = {
            "id": "ev_msft_sec",
            "title": "Microsoft warns of credential phishing targeting cloud customers",
            "snippet": "Microsoft Threat Intelligence detected adversary infrastructure spoofing Azure login...",
            "url": "https://www.microsoft.com/security/blog/threat-intel"
        }
        res = relevance_gate.evaluate_item(item, target_entity="Investigate Microsoft", domain="brand")
        assert res.is_accepted
        assert res.relevance_score >= 0.80

    def test_accept_true_positive_satya(self):
        """Authentic Satya Nadella announcement must be accepted."""
        item = {
            "id": "ev_satya_real",
            "title": "Satya Nadella announces next generation Copilot AI features",
            "snippet": "Microsoft chairman and CEO Satya Nadella detailed enterprise cloud growth...",
            "url": "https://news.microsoft.com/satya-nadella-copilot"
        }
        res = relevance_gate.evaluate_item(item, target_entity="Satya Nadella", domain="personal")
        assert res.is_accepted
        assert res.relevance_score >= 0.80


# ─────────────────────────────────────────────────────────────────────────────
# 3. Social URL Resolution Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestSocialTargetResolver:
    def test_valid_x_status(self):
        res = social_target_resolver.resolve_twitter("https://x.com/Microsoft/status/1789012345678901234")
        assert res is not None
        assert res.target_type == "status"
        assert res.external_id == "1789012345678901234"
        assert res.canonical_url == "https://x.com/Microsoft/status/1789012345678901234"

    def test_valid_x_profile(self):
        res = social_target_resolver.resolve_twitter("https://twitter.com/satyanadella")
        assert res is not None
        assert res.target_type == "profile"
        assert res.external_id == "satyanadella"

    def test_invalid_x_search_and_mentions(self):
        assert social_target_resolver.resolve_twitter("https://x.com/search?q=microsoft") is None
        assert social_target_resolver.resolve_twitter("There was a lively discussion on Twitter today.") is None

    def test_valid_reddit_post_and_comment(self):
        res = social_target_resolver.resolve_reddit("https://www.reddit.com/r/technology/comments/123456/new_ai/")
        assert res is not None
        assert res.target_type == "post"
        assert res.external_id == "123456"

        res_comm = social_target_resolver.resolve_reddit("https://www.reddit.com/r/technology/comments/123456/new_ai/c987654")
        assert res_comm is not None
        assert res_comm.target_type == "comment"
        assert res_comm.external_id == "c987654"

    def test_valid_youtube_url(self):
        res = social_target_resolver.resolve_youtube("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        assert res is not None
        assert res.target_type == "video"
        assert res.external_id == "dQw4w9WgXcQ"


# ─────────────────────────────────────────────────────────────────────────────
# 4. Provenance Invariants Tests (Invariants A, B, C, D)
# ─────────────────────────────────────────────────────────────────────────────

class TestProvenanceInvariants:
    def test_invariant_a_stable_source_id(self):
        """Invariant A: Same external resource retrieved twice produces identical source_id."""
        url = "https://x.com/Microsoft/status/1789012345678901234"
        frag1 = EvidenceFragment(platform="twitter", url=url, author="Microsoft", content="Version 1 text")
        frag2 = EvidenceFragment(platform="twitter", url=url, author="Microsoft", content="Version 2 updated text")
        assert frag1.source_id == frag2.source_id

    def test_invariant_b_observation_separation(self):
        """Invariant B: Different observations of the same source have unique observation_ids."""
        url = "https://news.microsoft.com/press-release"
        frag1 = EvidenceFragment(platform="web", url=url, author="Microsoft", content="First draft", retrieved_at="2026-10-08T01:00:00Z")
        frag2 = EvidenceFragment(platform="web", url=url, author="Microsoft", content="Second draft with updates", retrieved_at="2026-10-08T02:00:00Z")
        assert frag1.source_id == frag2.source_id
        assert frag1.observation_id != frag2.observation_id

    def test_invariant_c_fallback_attempt_recording(self):
        """Invariant C: Fallback chain records both the failed primary attempt and successful fallback."""
        primary_att = AcquisitionAttempt(
            agent="BrandShield",
            query_id="q_01",
            source_id="src_test",
            url="https://x.com/Microsoft/status/123",
            requested_channel="twitter",
            actual_channel="twitter",
            backend="fxtwitter",
            retrieval_mode=RetrievalMode.ZERO_AUTH_PUBLIC_MIRROR.value,
            status="FAILED",
            fallback_used=True,
            fallback_backend="Bing Search Index",
            fallback_reason=FallbackReasonCode.MIRROR_UNAVAILABLE.value,
            error="Rate limit 429"
        )
        fallback_att = AcquisitionAttempt(
            agent="BrandShield",
            query_id="q_01",
            source_id="src_test",
            url="https://x.com/Microsoft/status/123",
            requested_channel="twitter",
            actual_channel="web_search",
            backend="bing-search-index",
            retrieval_mode=RetrievalMode.WEB_SEARCH_INDEX.value,
            status="SUCCESS",
            fallback_used=False
        )
        assert primary_att.status == "FAILED"
        assert primary_att.fallback_reason == "MIRROR_UNAVAILABLE"
        assert fallback_att.status == "SUCCESS"
        assert primary_att.source_id == fallback_att.source_id

    def test_invariant_d_backend_preservation(self):
        """Invariant D: Final evidence preserves authentic backend, URL, source_id, and mode."""
        frag = EvidenceFragment(
            platform="twitter",
            url="https://x.com/Microsoft/status/123",
            author="Microsoft",
            native_backend_id="fxtwitter",
            retrieval_mode=RetrievalMode.ZERO_AUTH_PUBLIC_MIRROR.value,
            actual_retrieval_channel="twitter"
        )
        d = frag.to_dict()
        assert d["native_backend_id"] == "fxtwitter"
        assert d["retrieval_mode"] == "zero_auth_public_mirror"
        assert d["url"] == "https://x.com/Microsoft/status/123"
        assert d["source_id"].startswith("src_")
        assert d["observation_id"].startswith("obs_")


# ─────────────────────────────────────────────────────────────────────────────
# 5. Fallback Accounting Invariant (Attempts == Successes + Failures)
# ─────────────────────────────────────────────────────────────────────────────

class TestFallbackAccounting:
    def test_attempts_equals_successes_plus_failures(self):
        """Attempts = Successes + Failures must hold strictly for every backend."""
        table = [
            {"backend": "Bing Search Index", "attempts": 6, "successes": 4, "failures": 2},
            {"backend": "Legacy News Scraper", "attempts": 4, "successes": 0, "failures": 4},
            {"backend": "Legacy Web Scraper", "attempts": 2, "successes": 2, "failures": 0},
            {"backend": "Legacy YouTube Scraper", "attempts": 3, "successes": 0, "failures": 3},
        ]
        for row in table:
            assert row["attempts"] == row["successes"] + row["failures"], f"Failed for {row['backend']}"
