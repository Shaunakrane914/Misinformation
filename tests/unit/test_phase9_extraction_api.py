import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from backend.api.agent_reach import AgentReachExtractRequest, agent_reach_extract
from backend.services.agent_reach.channels import EvidenceFragment


def test_deep_extract_uses_native_policy_boundary_and_exact_passages(monkeypatch):
    calls = []

    def execute(**kwargs):
        calls.append(kwargs)
        return [EvidenceFragment(platform="Web", url="https://example.org/", content="Actual captured text",
                                 content_depth="PARTIAL_CONTENT")], {"status": "SUCCESS", "outcome": "DIRECT_CONTENT"}
    monkeypatch.setattr("backend.services.agent_reach.native.native_router.execute_channel_query", execute)
    result = agent_reach_extract(AgentReachExtractRequest(platform="web", query="https://example.org/", mode="deep"))
    assert calls[0]["max_chars"] == 8000
    assert calls[0]["include_comments"] is True
    assert result["evidence"][0]["extraction"]["passages"][0]["text"] == "Actual captured text"
    assert result["claim_support"] == "NOT_ASSESSED"
    assert result["source_completeness"] == "UNKNOWN"


def test_policy_denial_remains_visible_without_fake_records(monkeypatch):
    monkeypatch.setattr("backend.services.agent_reach.native.native_router.execute_channel_query", lambda **kwargs: (
        [], {"status": "SKIPPED", "outcome": "EXCLUDED", "runtime_decision": {"decision": "EXCLUDE"}},
    ))
    result = agent_reach_extract(AgentReachExtractRequest(platform="reddit", query="post"))
    assert result["status"] == "SKIPPED"
    assert result["evidence"] == [] and result["runtime_decision"] == "EXCLUDE"


@pytest.mark.parametrize("kwargs", [{"limit": 6}, {"max_chars": 20001}, {"mode": "unbounded"}, {"platform": "../private"}])
def test_invalid_extraction_budgets_rejected(kwargs):
    args = {"platform": "web", "query": "https://example.org/", **kwargs}
    with pytest.raises(ValidationError):
        AgentReachExtractRequest(**args)


def test_unsupported_operation_rejected():
    with pytest.raises(HTTPException) as error:
        agent_reach_extract(AgentReachExtractRequest(platform="web", operation="private_dump", query="x"))
    assert error.value.status_code == 422
