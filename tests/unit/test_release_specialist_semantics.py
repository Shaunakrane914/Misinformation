"""Calibration cases from release diagnosis; no independent accuracy claim."""
from unittest.mock import patch
from backend.agents.brandshield.agent import BrandShieldAgent


def test_reported_historical_enforcement_does_not_count_as_current_attacker():
    source = {"evidence_id": "report", "title": "Nike counterfeit goods sentencing report",
              "content": "Customs officers seized counterfeit Nike shoes according to court documents.\n\nOfficials reported that the counterfeit goods posed a safety hazard.",
              "url": "https://publisher.example/report", "platform": "Web", "content_depth": "PARTIAL_CONTENT"}
    agent = BrandShieldAgent()
    with patch.object(agent, "search_brand_evidence", return_value=([source], {}, {}, 0)):
        result = agent.scan("Nike")
    assert result["threat_count"] == 0
    assert len(result["threats"]) == 1
    report = result["threats"][0]
    assert report["type"] == "ENFORCEMENT_REPORT" and report["actor_url"] is None
    assert report["severity"] == "info" and report["confidence"] is None
    assert result["findings"][0]["is_threat"] is False
    assert result["counterfeits"] == [] and result["impersonations"] == []
