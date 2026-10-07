"""
Aegis Protocol — 4-Agent Comprehensive Adversarial Quality Evaluation Suite
=============================================================================
Integration test suite evaluating deterministic intelligence quality, epistemic
grounding, and adversarial resilience across all four domain engines:
  1. BrandShieldAgent
  2. TrendingAgent
  3. ScoutAgent
  4. PersonalWatchAgent
"""

import pytest
from scripts.evaluate_all_agents import AgentEvaluationRunner


@pytest.fixture(scope="module")
def eval_runner():
    return AgentEvaluationRunner(offline_mode=True)


@pytest.mark.integration
def test_brandshield_adversarial_quality(eval_runner):
    """
    Evaluates BrandShield across:
    - Genuine brands (Nike, Apple)
    - Counterfeit detection & attribution
    - Phishing & lookalike portal detection
    - Fake reviews vs legitimate complaints distinction
    - Zero evidence safety invariant (nonexistent entity)
    - Contradiction handling
    - Criticism false-positive challenge
    """
    results = eval_runner.evaluate_brandshield()
    assert len(results) >= 8

    for res in results:
        assert res["status"] == "PASS", f"Scenario {res['scenario']} failed: {res['notes']}"
        assert res["false_positive"] is False, f"False positive in {res['scenario']}"
        assert res["false_negative"] is False, f"False negative in {res['scenario']}"
        assert 0.0 <= res["retrieval_quality"] <= 1.0
        assert 0.0 <= res["grounding_quality"] <= 1.0


@pytest.mark.integration
def test_trending_adversarial_quality(eval_runner):
    """
    Evaluates Trending across:
    - Entity mode vs discovery mode resolution
    - Wire syndication deduplication (1 wire + 3 copies + 2 social != 6 independent sources)
    - Varied headline narrative clustering
    - Irrelevant noise rejection
    - Zero evidence safety invariant
    - Temporal velocity acceleration & inverted timestamp resilience
    """
    results = eval_runner.evaluate_trending()
    assert len(results) >= 6

    for res in results:
        assert res["status"] == "PASS", f"Scenario {res['scenario']} failed: {res['notes']}"
        assert res["false_positive"] is False, f"False positive in {res['scenario']}"
        assert res["false_negative"] is False, f"False negative in {res['scenario']}"
        assert 0.0 <= res["classification_quality"] <= 1.0


@pytest.mark.integration
def test_scout_adversarial_quality(eval_runner):
    """
    Evaluates Scout across:
    - Market telemetry z-score anomaly mapping
    - Nominal price trajectory invariant (no forced panic narrative)
    - Conflicting valuation contradiction extraction ($10B vs $13.5B)
    - Unconfirmed rumor epistemic guard (held in UNVERIFIED state)
    - Regulatory filing source tier precedence (Tier 1 vs commentary)
    """
    results = eval_runner.evaluate_scout()
    assert len(results) >= 5

    for res in results:
        assert res["status"] == "PASS", f"Scenario {res['scenario']} failed: {res['notes']}"
        assert res["false_positive"] is False, f"False positive in {res['scenario']}"
        assert res["false_negative"] is False, f"False negative in {res['scenario']}"
        assert res["grounding_quality"] == 1.0


@pytest.mark.integration
def test_personal_watch_adversarial_quality(eval_runner):
    """
    Evaluates Personal Watch across:
    - Normal executive activity (no false threat)
    - Impersonation account detection
    - Fake giveaway / scam classification
    - Deepfake / synthetic video detection
    - Privacy zero-leak filter (SSN & phone numbers scrubbed)
    - Multi-scan change detection (NEW_THREAT, ESCALATED_THREAT)
    """
    results = eval_runner.evaluate_personal_watch()
    assert len(results) >= 5

    for res in results:
        assert res["status"] == "PASS", f"Scenario {res['scenario']} failed: {res['notes']}"
        assert res["false_positive"] is False, f"False positive in {res['scenario']}"
        assert res["false_negative"] is False, f"False negative in {res['scenario']}"


@pytest.mark.integration
def test_cross_agent_and_prompt_injection_invariants(eval_runner):
    """
    Evaluates cross-agent misdirection, adversarial prompt injection resilience,
    and source provenance invariants.
    """
    results = eval_runner.evaluate_cross_agent_and_security()
    assert len(results) >= 2

    for res in results:
        assert res["status"] == "PASS", f"Scenario {res['scenario']} failed: {res['notes']}"
        assert res["false_positive"] is False


@pytest.mark.integration
def test_evaluation_runner_full_suite_metrics(eval_runner):
    """
    Validates complete 28-scenario execution report metrics and artifacts.
    """
    summary = eval_runner.run_all()
    assert summary["overall_quality_score_pct"] >= 95.0
    assert summary["total_scenarios"] >= 28
    assert summary["total_failed"] == 0
