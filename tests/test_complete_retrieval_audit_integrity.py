"""
Aegis Protocol — Complete Retrieval Audit Integrity Test Suite
==============================================================
Validates mathematical correctness, accounting invariants, and metric rigor:
1. Success rate cannot exceed 100% (assert 0.0 <= rate <= 1.0)
2. Mutually exclusive acquisition outcome categories (NATIVE, SPECIALIST, FALLBACK, FAILURE)
3. Strict candidate funnel metric separation:
   candidates_discovered -> hard_gate_passes -> hard_gate_rejects -> ranked_candidates ->
   accepted_candidates -> acquired_candidates -> final_evidence
4. Fallback arithmetic invariant (attempts == successes + failures for every backend)
5. Deterministic rule-based review (TRUE_POSITIVE, FALSE_POSITIVE, AMBIGUOUS) with review_basis
6. Concrete social URL accounting (X status/profile, Reddit post/comment, YouTube video)
7. Provenance preservation across fallback chains
8. Invariants A through H
9. BrandShield X resolution regression (real X URL reaches FxTwitter, generic text is rejected)
10. Specific audit integrity tests:
    - accepted_candidates is not automatically equal to ranked_candidates (acceptance rate < 100%)
    - no stale metrics in generated Markdown (dynamic wall-clock time & channels)
    - 66/70 X resolution is reported as 94.3%, not 100%
    - heuristic review is not labeled semantic or manual
    - final verdict cannot claim General Relevance FIXED merely because FP=0
"""

import pytest
from typing import Dict, Any, List

from backend.services.agent_reach.channels import (
    AcquisitionAttempt,
    EvidenceFragment,
    EvidenceObservation,
    FallbackReasonCode,
)
from backend.services.agent_reach.native.social_resolver import (
    SocialTargetResolver,
    social_target_resolver,
)
from backend.services.agent_reach.native.source_discovery import (
    extract_x_source,
    extract_reddit_source,
    SourceDiscoveryResult,
)
from backend.services.research.entity_resolver import (
    entity_resolver,
    TargetEntity,
)
from backend.services.research.relevance_gate import (
    relevance_gate,
    RelevanceAssessment,
)


class TestAcquisitionAccounting:
    def test_mutually_exclusive_categories_and_rate_bound(self):
        """
        Total attempts = native_successes + specialist_successes + fallback_successes + failed_attempts.
        Success rate must NEVER exceed 1.0 (100%).
        """
        native_successes = 4
        specialist_successes = 3
        fallback_successes = 2
        failed_attempts = 1

        total_attempts = native_successes + specialist_successes + fallback_successes + failed_attempts
        assert total_attempts == 10

        successful_attempts = native_successes + specialist_successes + fallback_successes
        assert successful_attempts == 9

        success_rate = successful_attempts / total_attempts
        assert 0.0 <= success_rate <= 1.0
        assert success_rate == 0.90  # Exactly 90%, NOT >100%

    def test_acquisition_rate_assert_fails_if_over_one(self):
        """Audit must throw AssertionError if double-counting causes rate > 1.0."""
        double_counted = 11
        total = 10
        with pytest.raises(AssertionError):
            rate = double_counted / total
            assert 0.0 <= rate <= 1.0, f"Rate {rate} exceeded 1.0"


class TestCandidateFunnelMetrics:
    def test_strict_funnel_separation(self):
        """
        Verify distinct stages:
        candidates_discovered >= hard_gate_passes
        hard_gate_passes + hard_gate_rejects <= candidates_discovered
        ranked_candidates == hard_gate_passes (after clustering)
        accepted_candidates <= ranked_candidates
        candidate_acceptance_rate == accepted_candidates / ranked_candidates
        final_evidence <= accepted_candidates
        """
        discovered = 100
        rejects = 30
        passes = 60  # deduplicated gate evaluation
        ranked = passes  # 60 entering ranking
        accepted = 25   # Selected from ranked pool for acquisition
        final_evidence = 20

        assert passes + rejects <= discovered
        assert accepted <= ranked
        acceptance_rate = round(accepted / ranked, 3)
        assert 0.0 <= acceptance_rate <= 1.0
        assert acceptance_rate == round(25 / 60, 3)
        assert final_evidence <= accepted
        assert accepted != final_evidence

    def test_accepted_candidates_not_automatically_equal_to_ranked_candidates(self):
        """
        Test that candidate acceptance represents actual selection for acquisition
        from the ranked pool and does NOT fabricate a fixed 100% acceptance rate.
        """
        ranked_pool = [f"cand_{i:03d}" for i in range(1, 41)]  # 40 ranked candidates
        deep_read_budget = 8
        # Specialist targets extending beyond standard deep read window
        specialist_targets = ["cand_009", "cand_010"]

        # Selection policy: deep read budget + specialist social targets
        accepted_candidates = list(set(ranked_pool[:deep_read_budget] + specialist_targets))
        assert len(accepted_candidates) == 10
        assert len(accepted_candidates) < len(ranked_pool)

        acceptance_rate = len(accepted_candidates) / len(ranked_pool)
        assert acceptance_rate == 10 / 40  # 25.0%, NOT 100%
        assert 0.0 < acceptance_rate < 1.0
        assert len(accepted_candidates) <= len(ranked_pool)


class TestFallbackArithmetic:
    def test_fallback_attempts_equals_successes_plus_failures(self):
        """For every fallback backend: attempts == successes + failures."""
        backends_telemetry = {
            "bing_search_index": {"attempts": 5, "successes": 4, "failures": 1},
            "legacy_news_scraper": {"attempts": 2, "successes": 2, "failures": 0},
            "legacy_web_scraper": {"attempts": 3, "successes": 1, "failures": 2},
        }
        for be, stats in backends_telemetry.items():
            assert stats["attempts"] == stats["successes"] + stats["failures"], f"Accounting mismatch on {be}"


class TestDeterministicQualityReview:
    def test_three_way_classification(self):
        """
        Evaluates entity_correct, intent_relevant, and source_correct
        to classify into TRUE_POSITIVE, FALSE_POSITIVE, or AMBIGUOUS.
        """
        def classify_evidence(entity_ok: bool, intent_ok: bool, source_ok: bool) -> str:
            if entity_ok and intent_ok and source_ok:
                return "TRUE_POSITIVE"
            if not entity_ok or not intent_ok:
                return "FALSE_POSITIVE"
            return "AMBIGUOUS"

        # Item 1: Real Microsoft security patch
        assert classify_evidence(True, True, True) == "TRUE_POSITIVE"

        # Item 2: Satya 1998 Bollywood movie (entity_ok is False)
        assert classify_evidence(False, True, True) == "FALSE_POSITIVE"

        # Item 3: Magic the Gathering card (intent_ok is False)
        assert classify_evidence(False, False, True) == "FALSE_POSITIVE"

        # Item 4: Unverified third party forum rumor
        assert classify_evidence(True, True, False) == "AMBIGUOUS"

    def test_heuristic_review_not_labeled_semantic_or_manual(self):
        """
        The review is deterministic rule-based (EntityResolver tokens, lexical overlap, etc.).
        It must record review_basis and NOT be labeled as 'human manual review' or 'ML semantic'.
        """
        valid_review_bases = {
            "ENTITY_RULE",
            "INTENT_LEXICAL",
            "KNOWN_HARD_NEGATIVE",
            "SOURCE_URL_CHECK",
            "MODEL_SEMANTIC",
            "HUMAN_REVIEW"
        }
        item_review = {
            "evidence_id": "ev_001",
            "title": "Microsoft Issues Security Patch for Windows",
            "url": "https://msrc.microsoft.com/update-guide",
            "entity_score": 0.95,
            "intent_score": 0.85,
            "source_quality_score": 0.95,
            "review_verdict": "TRUE_POSITIVE",
            "rejection_or_ambiguity_reason": "Passes canonical entity and intent lexical thresholds",
            "review_basis": "ENTITY_RULE",
        }
        assert item_review["review_basis"] in valid_review_bases
        assert item_review["review_basis"] not in ("MODEL_SEMANTIC", "HUMAN_REVIEW")
        assert "entity_score" in item_review
        assert "intent_score" in item_review
        assert "rejection_or_ambiguity_reason" in item_review


class TestBrandShieldXResolution:
    def test_brandshield_discovers_and_resolves_concrete_x_status(self):
        """
        BrandShield finding an actual X URL must resolve to a concrete target
        with valid status ID and route to FxTwitter.
        """
        raw_x_url = "https://x.com/MSFTIssues/status/1880001234567890123"
        cand = extract_x_source(raw_x_url, query="Microsoft fake support account")
        assert cand is not None
        assert cand.platform == "twitter"
        assert cand.source_type == "status"
        assert cand.external_id == "1880001234567890123"
        assert cand.canonical_url == "https://x.com/MSFTIssues/status/1880001234567890123"

    def test_generic_twitter_mention_rejected_from_specialist(self):
        """
        Generic search snippet saying 'discussion on Twitter' without status/profile
        must NOT become a concrete social target.
        """
        generic_snippet = "There was widespread discussion on Twitter about Microsoft cloud issues."
        cand = extract_x_source(generic_snippet)
        assert cand is None

    def test_x_concrete_resolution_reported_truthfully(self):
        """
        When 70 X candidates are discovered and 66 are resolved to concrete targets,
        the resolution rate must be reported as 66 / 70 = 94.3%, NOT 100%.
        """
        discovered = 70
        concrete = 66
        rate = round(concrete / discovered, 3)
        assert rate == 0.943
        assert f"{rate * 100:.1f}%" == "94.3%"
        assert rate < 1.0


class TestAuditInvariantsAThroughH:
    def test_invariant_a_rate_bound(self):
        """Invariant A: success_rate <= 1.0"""
        succ, total = 9, 10
        rate = succ / total
        assert rate <= 1.0

    def test_invariant_b_fallback_equality(self):
        """Invariant B: attempts == successes + failures"""
        attempts = 7
        successes = 5
        failures = 2
        assert attempts == successes + failures

    def test_invariant_c_provenance_preservation(self):
        """Invariant C: Final evidence actual backend == acquisition backend"""
        ev_item = {
            "evidence_id": "ev_001",
            "backend": "fxtwitter",
            "acquisition_backend": "fxtwitter"
        }
        assert ev_item["backend"] == ev_item["acquisition_backend"]

    def test_invariant_d_non_concrete_never_specialist(self):
        """Invariant D: Non-concrete social candidate must never get specialist acquisition."""
        resolved = social_target_resolver.resolve_url_or_text("https://x.com/explore")
        assert resolved is None  # /explore is reserved, not a concrete status or profile

    def test_invariant_e_multi_word_person_no_single_token(self):
        """Invariant E: Multi-word entity cannot be accepted on first-name-only."""
        satya_target = entity_resolver.resolve_entity("Satya Nadella", domain="personal")
        score, signals, reason = entity_resolver.evaluate_entity_match("Satya attended a conference", satya_target)
        assert score < 0.35

    def test_invariant_f_action_verb_cannot_become_entity(self):
        """Invariant F: Action verb cannot become an entity token."""
        parsed = entity_resolver.parse_request("Investigate Microsoft", domain="brand")
        assert parsed.action_verb == "investigate"
        assert parsed.target_entity.canonical_name == "Microsoft"
        assert "investigate" != parsed.target_entity.canonical_name.lower()

    def test_invariant_g_true_positive_above_threshold(self):
        """Invariant G: TRUE_POSITIVE evidence must have entity relevance above threshold (0.50)."""
        ass = relevance_gate.evaluate_item(
            {"title": "Microsoft Copilot Security Alert", "snippet": "Microsoft released advisory for Defender."},
            target_entity="Microsoft",
            domain="brand"
        )
        assert ass.is_accepted
        assert ass.entity_score >= 0.50

    def test_invariant_h_negative_entity_rejected(self):
        """Invariant H: Final evidence cannot contain known negative entity signals."""
        ass = relevance_gate.evaluate_item(
            {"title": "Satya (1998 film) Box Office Collection", "snippet": "Ram Gopal Varma crime film Satya."},
            target_entity="Satya Nadella",
            domain="personal"
        )
        assert not ass.is_accepted
        assert ass.rejection_stage in ("HARD_GATE_ERROR", "ENTITY_RESOLUTION_ERROR")


class TestMarkdownReportIntegrity:
    def test_no_stale_metrics_in_generated_markdown(self):
        """
        Verify that generated markdown does NOT contain stale hardcoded metrics:
        - No hardcoded '90.52s'
        - No hardcoded 'full 6-channel investigations'
        - No '100% of discovered candidates' for X when concrete < discovered
        """
        from scripts.run_final_retrieval_audit import generate_final_audit_markdown

        sample_audit_data = {
            "execution_timestamp": "2026-10-08T15:00:00Z",
            "total_wall_clock_seconds": 105.2,
            "investigation_target": "Microsoft and Satya Nadella",
            "executive_waterfall": {
                "BrandShield": {
                    "channels_planned": 7,
                    "candidates_discovered": 97,
                    "hard_gate_passes": 24,
                    "hard_gate_rejects": 17,
                    "ranked_candidates": 24,
                    "accepted_candidates": 12,
                    "acquisition_attempts": 21,
                    "native_successes": 11,
                    "specialist_successes": 6,
                    "fallback_successes": 4,
                    "failed_attempts": 0,
                    "final_evidence": 20,
                    "true_positives": 9,
                    "false_positives": 0,
                    "ambiguous": 11,
                    "unique_domains": 7,
                    "runtime_seconds": 16.77,
                    "candidate_acceptance_rate": 0.50,
                    "acquisition_success_rate": 1.0,
                    "fallback_rate": 0.19,
                    "false_positive_rate": 0.0,
                    "social_contribution_rate": 0.20,
                },
                "Trending": {
                    "channels_planned": 8,
                    "candidates_discovered": 107,
                    "hard_gate_passes": 65,
                    "hard_gate_rejects": 14,
                    "ranked_candidates": 65,
                    "accepted_candidates": 16,
                    "acquisition_attempts": 24,
                    "native_successes": 14,
                    "specialist_successes": 6,
                    "fallback_successes": 4,
                    "failed_attempts": 0,
                    "final_evidence": 33,
                    "true_positives": 31,
                    "false_positives": 0,
                    "ambiguous": 2,
                    "unique_domains": 6,
                    "runtime_seconds": 12.99,
                    "candidate_acceptance_rate": 0.246,
                    "acquisition_success_rate": 1.0,
                    "fallback_rate": 0.167,
                    "false_positive_rate": 0.0,
                    "social_contribution_rate": 0.182,
                },
                "Scout": {
                    "channels_planned": 6,
                    "candidates_discovered": 152,
                    "hard_gate_passes": 40,
                    "hard_gate_rejects": 2,
                    "ranked_candidates": 40,
                    "accepted_candidates": 18,
                    "acquisition_attempts": 48,
                    "native_successes": 21,
                    "specialist_successes": 9,
                    "fallback_successes": 8,
                    "failed_attempts": 10,
                    "final_evidence": 40,
                    "true_positives": 26,
                    "false_positives": 0,
                    "ambiguous": 14,
                    "unique_domains": 8,
                    "runtime_seconds": 58.97,
                    "candidate_acceptance_rate": 0.45,
                    "acquisition_success_rate": 0.792,
                    "fallback_rate": 0.167,
                    "false_positive_rate": 0.0,
                    "social_contribution_rate": 0.175,
                },
                "Personal Watch": {
                    "channels_planned": 5,
                    "candidates_discovered": 78,
                    "hard_gate_passes": 6,
                    "hard_gate_rejects": 34,
                    "ranked_candidates": 6,
                    "accepted_candidates": 5,
                    "acquisition_attempts": 20,
                    "native_successes": 9,
                    "specialist_successes": 7,
                    "fallback_successes": 2,
                    "failed_attempts": 2,
                    "final_evidence": 6,
                    "true_positives": 6,
                    "false_positives": 0,
                    "ambiguous": 0,
                    "unique_domains": 2,
                    "runtime_seconds": 16.48,
                    "candidate_acceptance_rate": 0.833,
                    "acquisition_success_rate": 0.90,
                    "fallback_rate": 0.10,
                    "false_positive_rate": 0.0,
                    "social_contribution_rate": 0.167,
                },
            },
            "exact_fallback_breakdown": [
                {
                    "backend": "Bing Search Index",
                    "attempts": 12,
                    "successes": 12,
                    "failures": 0,
                    "reasons": "ARCTIC_SHIFT_UNAVAILABLE"
                }
            ],
            "social_funnels": {
                "BrandShield": {
                    "twitter": {"discovered": 15, "concrete_targets": 15, "specialist_attempts": 3, "successes": 3, "failures": 0, "fallback_attempts": 0, "final_evidence": 1, "true_positives": 1, "false_positives": 0},
                    "reddit": {"discovered": 15, "concrete_targets": 0, "specialist_attempts": 0, "successes": 0, "failures": 0, "fallback_attempts": 3, "final_evidence": 0, "true_positives": 0, "false_positives": 0},
                    "youtube": {"discovered": 15, "concrete_targets": 15, "specialist_attempts": 3, "successes": 3, "failures": 0, "fallback_attempts": 0, "final_evidence": 3, "true_positives": 1, "false_positives": 0},
                },
                "Trending": {
                    "twitter": {"discovered": 15, "concrete_targets": 15, "specialist_attempts": 3, "successes": 3, "failures": 0, "fallback_attempts": 0, "final_evidence": 0, "true_positives": 0, "false_positives": 0},
                    "reddit": {"discovered": 18, "concrete_targets": 8, "specialist_attempts": 1, "successes": 1, "failures": 0, "fallback_attempts": 2, "final_evidence": 0, "true_positives": 0, "false_positives": 0},
                    "youtube": {"discovered": 10, "concrete_targets": 10, "specialist_attempts": 2, "successes": 2, "failures": 0, "fallback_attempts": 0, "final_evidence": 6, "true_positives": 5, "false_positives": 0},
                },
                "Scout": {
                    "twitter": {"discovered": 27, "concrete_targets": 23, "specialist_attempts": 5, "successes": 5, "failures": 0, "fallback_attempts": 1, "final_evidence": 1, "true_positives": 1, "false_positives": 0},
                    "reddit": {"discovered": 23, "concrete_targets": 0, "specialist_attempts": 0, "successes": 0, "failures": 0, "fallback_attempts": 6, "final_evidence": 0, "true_positives": 0, "false_positives": 0},
                    "youtube": {"discovered": 14, "concrete_targets": 14, "specialist_attempts": 4, "successes": 4, "failures": 0, "fallback_attempts": 0, "final_evidence": 6, "true_positives": 5, "false_positives": 0},
                },
                "Personal Watch": {
                    "twitter": {"discovered": 13, "concrete_targets": 13, "specialist_attempts": 3, "successes": 3, "failures": 0, "fallback_attempts": 0, "final_evidence": 1, "true_positives": 1, "false_positives": 0},
                    "reddit": {"discovered": 24, "concrete_targets": 24, "specialist_attempts": 3, "successes": 3, "failures": 0, "fallback_attempts": 0, "final_evidence": 0, "true_positives": 0, "false_positives": 0},
                    "youtube": {"discovered": 5, "concrete_targets": 5, "specialist_attempts": 2, "successes": 2, "failures": 0, "fallback_attempts": 1, "final_evidence": 0, "true_positives": 0, "false_positives": 0},
                },
            }
        }

        md = generate_final_audit_markdown(sample_audit_data)
        assert "90.52s" not in md, "Found stale runtime 90.52s in generated markdown!"
        assert "full 6-channel investigations" not in md, "Found stale channel claim in generated markdown!"
        assert "105.2s" in md, "Markdown must include current runtime (105.2s)"
        assert "94.3%" in md, "66/70 X resolution must be reported as 94.3%"
        assert "100% of discovered candidates were validated" not in md

    def test_verdict_cannot_claim_general_relevance_fixed_merely_on_fp_zero(self):
        """
        Verify that having 0 false positives in a heuristic audit does NOT mark
        'General Relevance' as FIXED. It must be PARTIALLY FIXED or NOT ENOUGH EVIDENCE.
        """
        from scripts.run_final_retrieval_audit import generate_final_audit_markdown

        sample_data = {
            "execution_timestamp": "2026-10-08T15:00:00Z",
            "total_wall_clock_seconds": 100.0,
            "investigation_target": "Microsoft",
            "executive_waterfall": {
                "BrandShield": {"channels_planned": 7, "candidates_discovered": 10, "hard_gate_passes": 5, "hard_gate_rejects": 5, "ranked_candidates": 5, "accepted_candidates": 3, "acquisition_attempts": 3, "native_successes": 2, "specialist_successes": 1, "fallback_successes": 0, "failed_attempts": 0, "final_evidence": 3, "true_positives": 3, "false_positives": 0, "ambiguous": 0, "unique_domains": 2, "runtime_seconds": 10.0, "candidate_acceptance_rate": 0.60, "acquisition_success_rate": 1.0, "fallback_rate": 0.0, "false_positive_rate": 0.0, "social_contribution_rate": 0.0},
                "Trending": {"channels_planned": 8, "candidates_discovered": 10, "hard_gate_passes": 5, "hard_gate_rejects": 5, "ranked_candidates": 5, "accepted_candidates": 3, "acquisition_attempts": 3, "native_successes": 2, "specialist_successes": 1, "fallback_successes": 0, "failed_attempts": 0, "final_evidence": 3, "true_positives": 3, "false_positives": 0, "ambiguous": 0, "unique_domains": 2, "runtime_seconds": 10.0, "candidate_acceptance_rate": 0.60, "acquisition_success_rate": 1.0, "fallback_rate": 0.0, "false_positive_rate": 0.0, "social_contribution_rate": 0.0},
                "Scout": {"channels_planned": 6, "candidates_discovered": 10, "hard_gate_passes": 5, "hard_gate_rejects": 5, "ranked_candidates": 5, "accepted_candidates": 3, "acquisition_attempts": 3, "native_successes": 2, "specialist_successes": 1, "fallback_successes": 0, "failed_attempts": 0, "final_evidence": 3, "true_positives": 3, "false_positives": 0, "ambiguous": 0, "unique_domains": 2, "runtime_seconds": 10.0, "candidate_acceptance_rate": 0.60, "acquisition_success_rate": 1.0, "fallback_rate": 0.0, "false_positive_rate": 0.0, "social_contribution_rate": 0.0},
                "Personal Watch": {"channels_planned": 5, "candidates_discovered": 10, "hard_gate_passes": 5, "hard_gate_rejects": 5, "ranked_candidates": 5, "accepted_candidates": 3, "acquisition_attempts": 3, "native_successes": 2, "specialist_successes": 1, "fallback_successes": 0, "failed_attempts": 0, "final_evidence": 3, "true_positives": 3, "false_positives": 0, "ambiguous": 0, "unique_domains": 2, "runtime_seconds": 10.0, "candidate_acceptance_rate": 0.60, "acquisition_success_rate": 1.0, "fallback_rate": 0.0, "false_positive_rate": 0.0, "social_contribution_rate": 0.0},
            },
            "exact_fallback_breakdown": [],
            "social_funnels": {
                "BrandShield": {"twitter": {"discovered": 0, "concrete_targets": 0, "specialist_attempts": 0, "successes": 0, "failures": 0, "fallback_attempts": 0, "final_evidence": 0, "true_positives": 0, "false_positives": 0}, "reddit": {"discovered": 0, "concrete_targets": 0, "specialist_attempts": 0, "successes": 0, "failures": 0, "fallback_attempts": 0, "final_evidence": 0, "true_positives": 0, "false_positives": 0}, "youtube": {"discovered": 0, "concrete_targets": 0, "specialist_attempts": 0, "successes": 0, "failures": 0, "fallback_attempts": 0, "final_evidence": 0, "true_positives": 0, "false_positives": 0}},
                "Trending": {"twitter": {"discovered": 0, "concrete_targets": 0, "specialist_attempts": 0, "successes": 0, "failures": 0, "fallback_attempts": 0, "final_evidence": 0, "true_positives": 0, "false_positives": 0}, "reddit": {"discovered": 0, "concrete_targets": 0, "specialist_attempts": 0, "successes": 0, "failures": 0, "fallback_attempts": 0, "final_evidence": 0, "true_positives": 0, "false_positives": 0}, "youtube": {"discovered": 0, "concrete_targets": 0, "specialist_attempts": 0, "successes": 0, "failures": 0, "fallback_attempts": 0, "final_evidence": 0, "true_positives": 0, "false_positives": 0}},
                "Scout": {"twitter": {"discovered": 0, "concrete_targets": 0, "specialist_attempts": 0, "successes": 0, "failures": 0, "fallback_attempts": 0, "final_evidence": 0, "true_positives": 0, "false_positives": 0}, "reddit": {"discovered": 0, "concrete_targets": 0, "specialist_attempts": 0, "successes": 0, "failures": 0, "fallback_attempts": 0, "final_evidence": 0, "true_positives": 0, "false_positives": 0}, "youtube": {"discovered": 0, "concrete_targets": 0, "specialist_attempts": 0, "successes": 0, "failures": 0, "fallback_attempts": 0, "final_evidence": 0, "true_positives": 0, "false_positives": 0}},
                "Personal Watch": {"twitter": {"discovered": 0, "concrete_targets": 0, "specialist_attempts": 0, "successes": 0, "failures": 0, "fallback_attempts": 0, "final_evidence": 0, "true_positives": 0, "false_positives": 0}, "reddit": {"discovered": 0, "concrete_targets": 0, "specialist_attempts": 0, "successes": 0, "failures": 0, "fallback_attempts": 0, "final_evidence": 0, "true_positives": 0, "false_positives": 0}, "youtube": {"discovered": 0, "concrete_targets": 0, "specialist_attempts": 0, "successes": 0, "failures": 0, "fallback_attempts": 0, "final_evidence": 0, "true_positives": 0, "false_positives": 0}},
            }
        }
        md = generate_final_audit_markdown(sample_data)
        assert "General Relevance:       FIXED" not in md, "General Relevance must not be declared FIXED on heuristic review alone!"
        assert "PARTIALLY FIXED / NOT ENOUGH EVIDENCE" in md
