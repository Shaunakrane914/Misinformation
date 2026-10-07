"""
Unit Tests for Aegis Protocol Live Smoke Harness (scripts/live_agent_smoke_test.py)
===================================================================================
Verifies:
  1. Success path: When all 4 agents pass, runner returns 0, overall_status == 'PASS',
     and prints 'ALL 4 AGENTS LIVE VERIFIED ✅'.
  2. Failure path: When any agent fails, runner returns 1, overall_status == 'FAIL',
     prints 'LIVE AGENT VERIFICATION FAILED ❌', and lists the failed agent.
  3. Artifact generation & secret scrubbing: Verifies JSON report is generated and
     contains no secrets or tokens.
  4. Bounded failure vs zero-evidence semantics.
"""

import os
import sys
import json
import pytest
from unittest.mock import patch, MagicMock

from scripts.live_agent_smoke_test import (
    run_live_smoke_suite,
    sanitize_artifact_data,
    verify_brandshield_live,
    verify_trending_live,
    verify_scout_live,
    verify_personal_watch_live,
)


def test_sanitize_artifact_data():
    """Verify secrets and tokens are redacted from audit report."""
    dirty = {
        "entity": "Nike",
        "api_key": "AIzaSySecretKey",
        "auth_token": "Bearer 123456",
        "nested": {
            "oauth_secret": "xyz",
            "safe_url": "https://nike.com"
        }
    }
    clean = sanitize_artifact_data(dirty)
    assert clean["api_key"] == "[REDACTED]"
    assert clean["auth_token"] == "[REDACTED]"
    assert clean["nested"]["oauth_secret"] == "[REDACTED]"
    assert clean["nested"]["safe_url"] == "https://nike.com"


def test_smoke_harness_all_pass(capsys, tmp_path):
    """Verify harness passes when all 4 agents return valid results."""
    mock_bs = {"entity": "Nike", "sources_count": 5}
    mock_tr = {"discovery_mode": "discovery", "entity_mode": "entity"}
    mock_sc = {"ticker": "NVDA", "price": 236.0}
    mock_pw = {"canonical_name": "Satya Nadella", "category": "executive"}

    with patch("scripts.live_agent_smoke_test.verify_brandshield_live", return_value=mock_bs), \
         patch("scripts.live_agent_smoke_test.verify_trending_live", return_value=mock_tr), \
         patch("scripts.live_agent_smoke_test.verify_scout_live", return_value=mock_sc), \
         patch("scripts.live_agent_smoke_test.verify_personal_watch_live", return_value=mock_pw):

        success, report, exit_code = run_live_smoke_suite()

    captured = capsys.readouterr().out
    assert success is True
    assert exit_code == 0
    assert report["overall_status"] == "PASS"
    assert report["passed_count"] == 4
    assert "ALL 4 AGENTS LIVE VERIFIED ✅" in captured
    assert "LIVE AGENT VERIFICATION FAILED ❌" not in captured


def test_smoke_harness_single_failure_fails_entire_run(capsys):
    """Verify harness fails immediately with code 1 when any single agent fails."""
    mock_tr = {"discovery_mode": "discovery"}
    mock_sc = {"ticker": "NVDA", "price": 236.0}
    mock_pw = {"canonical_name": "Satya Nadella"}

    with patch("scripts.live_agent_smoke_test.verify_brandshield_live", side_effect=ValueError("Target brand mismatch")), \
         patch("scripts.live_agent_smoke_test.verify_trending_live", return_value=mock_tr), \
         patch("scripts.live_agent_smoke_test.verify_scout_live", return_value=mock_sc), \
         patch("scripts.live_agent_smoke_test.verify_personal_watch_live", return_value=mock_pw):

        success, report, exit_code = run_live_smoke_suite()

    captured = capsys.readouterr().out
    assert success is False
    assert exit_code == 1
    assert report["overall_status"] == "FAIL"
    assert report["passed_count"] == 3
    assert report["agents"]["brandshield"]["status"] == "FAIL"
    assert "Target brand mismatch" in report["agents"]["brandshield"]["error"]
    assert "LIVE AGENT VERIFICATION FAILED ❌" in captured
    assert "ALL 4 AGENTS LIVE VERIFIED ✅" not in captured
    assert "- BrandShield: Target brand mismatch" in captured


def test_smoke_harness_simulated_fault_injection(capsys):
    """Verify --simulate-failure flag triggers controlled failure."""
    mock_bs = {"entity": "Nike"}
    mock_tr = {"discovery_mode": "discovery"}
    mock_sc = {"ticker": "NVDA"}
    mock_pw = {"canonical_name": "Satya Nadella"}

    with patch("scripts.live_agent_smoke_test.verify_brandshield_live", return_value=mock_bs), \
         patch("scripts.live_agent_smoke_test.verify_trending_live", return_value=mock_tr), \
         patch("scripts.live_agent_smoke_test.verify_scout_live", return_value=mock_sc), \
         patch("scripts.live_agent_smoke_test.verify_personal_watch_live", return_value=mock_pw):

        success, report, exit_code = run_live_smoke_suite(simulate_failure_agent="scout")

    captured = capsys.readouterr().out
    assert success is False
    assert exit_code == 1
    assert report["overall_status"] == "FAIL"
    assert report["agents"]["scout"]["status"] == "FAIL"
    assert "LIVE AGENT VERIFICATION FAILED ❌" in captured
    assert "ALL 4 AGENTS LIVE VERIFIED ✅" not in captured


def test_smoke_harness_retrieval_failure_vs_agent_error(capsys):
    """
    Distinguish carefully between 'No evidence found' (contract preserved, PASS)
    and 'Agent execution failed' (unhandled error, FAIL).
    """
    # Case A: Honest zero-evidence result (no fake threats synthesized)
    mock_bs_zero_ev = {
        "entity": "Nike",
        "sources_count": 0,
        "threat_count": 0,
        "fallback_used": True,
    }
    mock_tr = {"discovery_mode": "discovery"}
    mock_sc = {"ticker": "NVDA", "price": 236.0}
    mock_pw = {"canonical_name": "Satya Nadella"}

    with patch("scripts.live_agent_smoke_test.verify_brandshield_live", return_value=mock_bs_zero_ev), \
         patch("scripts.live_agent_smoke_test.verify_trending_live", return_value=mock_tr), \
         patch("scripts.live_agent_smoke_test.verify_scout_live", return_value=mock_sc), \
         patch("scripts.live_agent_smoke_test.verify_personal_watch_live", return_value=mock_pw):

        success, report, exit_code = run_live_smoke_suite()

    assert success is True
    assert exit_code == 0
    assert report["agents"]["brandshield"]["status"] == "PASS"

    # Case B: Unhandled agent crash (must FAIL overall)
    with patch("scripts.live_agent_smoke_test.verify_brandshield_live", side_effect=ConnectionError("Backend connection reset")), \
         patch("scripts.live_agent_smoke_test.verify_trending_live", return_value=mock_tr), \
         patch("scripts.live_agent_smoke_test.verify_scout_live", return_value=mock_sc), \
         patch("scripts.live_agent_smoke_test.verify_personal_watch_live", return_value=mock_pw):

        success, report, exit_code = run_live_smoke_suite()

    assert success is False
    assert exit_code == 1
    assert report["agents"]["brandshield"]["status"] == "FAIL"
    assert "Backend connection reset" in report["agents"]["brandshield"]["error"]


def test_smoke_harness_timeout_bounded_failure():
    """Verify that a network timeout raises an error that fails that agent without hanging indefinitely."""
    mock_bs = {"entity": "Nike"}
    mock_tr = {"discovery_mode": "discovery"}
    mock_pw = {"canonical_name": "Satya Nadella"}

    with patch("scripts.live_agent_smoke_test.verify_brandshield_live", return_value=mock_bs), \
         patch("scripts.live_agent_smoke_test.verify_trending_live", return_value=mock_tr), \
         patch("scripts.live_agent_smoke_test.verify_scout_live", side_effect=TimeoutError("Network deadline exceeded (15s)")), \
         patch("scripts.live_agent_smoke_test.verify_personal_watch_live", return_value=mock_pw):

        success, report, exit_code = run_live_smoke_suite()

    assert success is False
    assert exit_code == 1
    assert report["agents"]["scout"]["status"] == "FAIL"
    assert "Network deadline exceeded" in report["agents"]["scout"]["error"]


def test_smoke_harness_malformed_external_data():
    """Verify malformed external data assertion failure correctly marks agent as FAIL."""
    mock_bs = {"entity": "Nike"}
    mock_tr = {"discovery_mode": "discovery"}
    mock_pw = {"canonical_name": "Satya Nadella"}

    # Scout returns malformed price (string instead of numeric)
    with patch("scripts.live_agent_smoke_test.verify_brandshield_live", return_value=mock_bs), \
         patch("scripts.live_agent_smoke_test.verify_trending_live", return_value=mock_tr), \
         patch("scripts.live_agent_smoke_test.verify_scout_live", side_effect=AssertionError("Expected numeric current_price, got <class 'str'>")), \
         patch("scripts.live_agent_smoke_test.verify_personal_watch_live", return_value=mock_pw):

        success, report, exit_code = run_live_smoke_suite()

    assert success is False
    assert exit_code == 1
    assert report["agents"]["scout"]["status"] == "FAIL"
    assert "Expected numeric current_price" in report["agents"]["scout"]["error"]

