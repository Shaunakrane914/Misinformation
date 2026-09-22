"""
Aegis Protocol — Unit Tests for Research & Investigator Agents
==============================================================
Validates JSON extraction, taxonomy normalization, confidence clamping,
insufficient evidence fallbacks, and singleton resolution.
"""

import json
import pytest
from backend.agents.research_agent import ResearchAgent
from backend.agents.investigator_agent import InvestigatorAgent, get_investigator_agent
from backend.schemas.claim_schemas import VerdictType, SeverityLevel


@pytest.mark.unit
def test_research_agent_extract_json_valid():
    """Test research agent parses valid JSON enclosed in markdown code fences."""
    agent = ResearchAgent()
    raw = """```json
{
  "supporting_evidence": ["Evidence Alpha", "Evidence Beta"],
  "refuting_evidence": ["Evidence Gamma"],
  "overall_evidence_confidence": 0.85,
  "sources_analyzed": ["Reuters", "AP News"]
}
```"""
    parsed = agent.extract_json(raw)
    assert len(parsed["supporting_evidence"]) == 2
    assert len(parsed["refuting_evidence"]) == 1
    assert parsed["overall_evidence_confidence"] == 0.85
    assert "Reuters" in parsed["sources_analyzed"]


@pytest.mark.unit
def test_research_agent_extract_json_fallback_on_malformed():
    """Test research agent fallback on corrupt or empty string."""
    agent = ResearchAgent()
    fallback = agent.extract_json("Not a JSON document at all")
    assert fallback["supporting_evidence"] == []
    assert fallback["refuting_evidence"] == []
    assert fallback["overall_evidence_confidence"] == 0.5


@pytest.mark.unit
def test_investigator_agent_extract_verdict_canonical_mapping():
    """Test investigator agent maps lowercase and raw strings to canonical VerdictType."""
    agent = InvestigatorAgent()
    raw = json.dumps({
        "verdict": "false",
        "confidence": 0.92,
        "severity": "high",
        "reasoning": "Claim is disproven by official statistics.",
        "explanation": "Primary datasets demonstrate otherwise.",
        "evidence_limitations": []
    })
    res = agent.extract_verdict(raw)
    assert res["verdict"] == VerdictType.FALSE.value
    assert res["severity"] == SeverityLevel.HIGH.value
    assert res["confidence"] == 0.92


@pytest.mark.unit
def test_investigator_agent_confidence_clamping():
    """Test investigator agent bounds confidence between 0.0 and 1.0."""
    agent = InvestigatorAgent()
    raw_over = json.dumps({"verdict": "True", "confidence": 1.5, "severity": "Low"})
    raw_under = json.dumps({"verdict": "True", "confidence": -0.2, "severity": "Low"})
    
    assert agent.extract_verdict(raw_over)["confidence"] == 1.0
    assert agent.extract_verdict(raw_under)["confidence"] == 0.0


@pytest.mark.unit
def test_investigator_agent_insufficient_evidence_heuristic():
    """Test investigator returns Insufficient Evidence verdict when evidence is empty."""
    agent = InvestigatorAgent()
    empty_evidence = {
        "supporting_evidence": [],
        "refuting_evidence": [],
        "overall_evidence_confidence": 0.5
    }
    raw = agent.determine_verdict("Sample query without data", empty_evidence)
    res = json.loads(raw)
    assert res["verdict"] == VerdictType.INSUFFICIENT_EVIDENCE.value
    assert res["severity"] == "Low"


@pytest.mark.unit
def test_investigator_agent_singleton_identity():
    """Test get_investigator_agent returns consistent singleton."""
    inst1 = get_investigator_agent()
    inst2 = get_investigator_agent()
    assert inst1 is inst2
