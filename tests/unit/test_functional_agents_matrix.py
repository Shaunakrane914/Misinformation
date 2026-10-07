"""
Aegis Protocol — Functional Agent Testing Matrix (CI Execution Bridge)
======================================================================
Wires the comprehensive 4-agent behavioral test matrix into the automated
CI suite executed across all Python versions (3.11, 3.12, 3.13) under tests/unit/.
"""

from tests.integration.test_functional_agents_matrix import (  # noqa: F401, F403
    fast_offline_llm_fixture,
    test_brandshield_normal_positive_case,
    test_brandshield_structured_intelligence_interface,
    test_trending_normal_positive_case,
    test_scout_normal_positive_case,
    test_personal_watch_normal_positive_case,
    test_brandshield_zero_evidence_guard,
    test_personal_watch_zero_evidence_guard,
    test_scout_contradiction_detection_conflicting_numbers,
    test_trending_source_independence_clustering,
    test_brandshield_threat_taxonomy_differentiation,
    test_personal_watch_threat_taxonomy_differentiation,
    test_personal_watch_consecutive_scan_change_detection,
    test_scout_financial_telemetry_and_anomalies,
    test_retrieval_failure_fallback_disclosure,
    test_scenario_01_brandshield_nike_counterfeit,
    test_scenario_02_brandshield_apple_fake_website,
    test_scenario_03_trending_whats_trending_in_ai,
    test_scenario_04_trending_openai_entity_mode,
    test_scenario_05_scout_nvda_stock_and_intelligence,
    test_scenario_06_scout_nvda_latest_earnings,
    test_scenario_07_scout_reliance_regulatory_investigation,
    test_scenario_08_personal_watch_public_executive_profile,
    test_scenario_09_personal_watch_impersonation_scam,
    test_scenario_10_personal_watch_run_twice_change_detection,
)
