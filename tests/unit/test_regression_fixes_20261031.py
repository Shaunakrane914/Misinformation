"""Tests verifying the October 31 production acquisition repairs on main."""

from unittest.mock import MagicMock, patch
from backend.services.agent_reach.source_planner import SourcePlanningEngine
from backend.infrastructure.acquisition.routing.router import NativeRouter


def test_dual_listed_adr_plans_sec_edgar():
    """Verify that dual-listed Indian ADR companies (like Infosys) receive SEC EDGAR planning."""
    planner = SourcePlanningEngine()
    plan = planner.plan(
        "Infosys overstated quarterly ADR revenue in SEC disclosures",
        entity="Infosys",
        domain="financial",
        agent="scout",
    )
    # Check if sec_edgar search is planned
    sec_actions = [a for a in plan.actions if a.channel == "sec_edgar"]
    assert len(sec_actions) > 0, "Expected sec_edgar action for dual-listed ADR entity Infosys"
    assert "regulatory_filing" in sec_actions[0].source_category
    assert sec_actions[0].authoritative is True


def test_technical_product_retains_github_channel():
    """Verify that technical targets retain github in planned actions when keywords match."""
    planner = SourcePlanningEngine()
    plan = planner.plan(
        "vLLM framework releases critical vulnerability in python code repository",
        entity="vLLM",
        domain="technical",
        agent="scout",
    )
    github_actions = [a for a in plan.actions if a.channel == "github"]
    assert len(github_actions) > 0, "Expected github action for technical framework query"
    assert github_actions[0].source_category == "technical_repository"


@patch("yt_dlp.YoutubeDL")
@patch("backend.infrastructure.acquisition.routing.router.is_safe_url", return_value=(True, ""))
def test_youtube_channel_read_enriches_with_transcript(_safe, mock_ydl_cls):
    """Verify NativeRouter.execute_channel_read enriches YouTube content with spoken transcripts."""
    mock_ydl_instance = MagicMock()
    mock_ydl_instance.__enter__.return_value = mock_ydl_instance
    mock_ydl_instance.extract_info.return_value = {
        "id": "mock_video_123",
        "title": "Quarterly Earnings Call",
        "uploader": "Corporate IR",
        "description": "Short description of earnings",
    }
    mock_ydl_cls.return_value = mock_ydl_instance

    router = NativeRouter()
    # Mock executor
    router.executor = MagicMock()
    router.executor.execute_youtube_transcript.return_value = {
        "status": "SUCCESS",
        "content": "WEBVTT\n\n00:00:01.000 --> 00:00:04.000\nGood morning everyone and welcome to the call."
    }

    res = router.execute_channel_read("https://www.youtube.com/watch?v=mock_video_123")
    assert res["status"] == "success"
    assert "Transcript:" in res["content"]
    assert "Good morning everyone and welcome to the call." in res["content"]
    assert res["title"] == "Quarterly Earnings Call"
