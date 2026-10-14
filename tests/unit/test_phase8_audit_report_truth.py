"""Outcome separation and credential safety for the independent live audit."""

import json

from scripts.audits.run_realworld_investigation_audit import (
    render_report, sanitize_audit_data, summarize_response,
)
from backend.infrastructure.acquisition.adapters.authoritative.fact_check import fetch_fact_check_claims
from backend.infrastructure.acquisition.network.http import BoundedHTTPResponse, ProviderHTTPError


def test_empty_http_success_is_not_research_success():
    result = summarize_response(200, {"evidence": [], "stock": {"current_price": 10}}, 1)
    assert result["execution"] == "PASS"
    assert result["returned_record_count"] == 0
    assert result["coverage"] == "NO_RETURNED_EVIDENCE"
    assert result["conclusion_correctness"] == "NOT_VERIFIED"
    assert result["independent_precision"] is None


def test_report_has_no_canned_conclusions_or_attached_fake_citations():
    result = summarize_response(200, {"sources": []}, 1)
    report = render_report({"commit": "test", "dirty": True, "observed_at_utc": "test",
                            "requests": {"scout": {}}, "agents": {"scout": result}})
    assert "**PARTIAL**" in report
    assert "Stable capital position" not in report
    assert "Copilot" not in report
    assert "MSFT-YF-DELAYED" not in report


def test_redaction_preserves_author_and_authority_metadata():
    result = sanitize_audit_data({"author": "Public Publisher", "source_authority": "REGULATOR",
                                  "api_key": "test-key", "url": "https://api.example/?key=test-key"})
    assert result["author"] == "Public Publisher"
    assert result["source_authority"] == "REGULATOR"
    assert "test-key" not in json.dumps(result)


def test_factcheck_credentials_never_enter_transport_url_or_error(caplog):
    secret = "test-private-api-key"
    def fetcher(url, **kwargs):
        assert secret not in url
        assert kwargs["headers"]["X-Goog-Api-Key"] == secret
        raise ProviderHTTPError(secret, endpoint=url, status_code=403, network_observed=True)
    result = fetch_fact_check_claims("public query", api_key=secret, http_fetcher=fetcher)
    assert result["status"] == "AUTH_REQUIRED"
    assert secret not in json.dumps(result)
    assert secret not in caplog.text


def test_factcheck_missing_credentials_requires_no_network(monkeypatch):
    monkeypatch.delenv("GOOGLE_FACTCHECK_API_KEY", raising=False)
    def forbidden(*args, **kwargs):
        raise AssertionError("network should not run")
    result = fetch_fact_check_claims("claim", http_fetcher=forbidden)
    assert result["status"] == "AUTH_REQUIRED"


def test_provider_summary_mapping_is_not_an_evidence_list():
    result = summarize_response(200, {"sources": {"reddit": 0}, "evidence": []}, 1)
    report = render_report({"commit": "test", "dirty": True, "observed_at_utc": "test",
                            "requests": {"trending": {}}, "agents": {"trending": result}})
    assert "No evidence records returned" in report


def test_scout_grouped_catalysts_and_canonical_sources_survive_report_adapter():
    from backend.services.report_builder import ReportBuilder
    report = ReportBuilder.from_scout_result(query="ACME", scout_data={
        "catalysts": {"unresolved": [{"factor": "Disclosure needs review"}]},
        "contradictions": {"for": [], "against": [], "unresolved": []},
        "news": {"company": []}, "social": {"reddit": []},
        "sources": [{"title": "Disclosure", "url": "https://example.org/disclosure"}],
    }).to_dict()
    assert report["findings"] == ["unresolved: Disclosure needs review"]
    assert len(report["evidence"]["independent"]) == 1


def test_sec_without_owner_contact_does_not_claim_compliant_identity(monkeypatch):
    from backend.infrastructure.acquisition.adapters.authoritative.sec_edgar import fetch_sec_submissions
    monkeypatch.delenv("SEC_USER_AGENT", raising=False)
    result = fetch_sec_submissions("AAPL")
    assert result["status"] == "CONFIG_REQUIRED"
    assert result["transport"]["network_observed"] is False


def test_authoritative_routes_registered_in_actual_shared_service(monkeypatch):
    from backend.infrastructure.acquisition.service import AgentReachService
    from backend.infrastructure.acquisition.adapters.authoritative.channel import AcquisitionOutcomeError
    from backend.services.agent_reach.native import native_router
    service = AgentReachService()
    assert {"sec_edgar", "nist_cve", "arxiv", "fact_check"}.issubset(service.registry.channel_names)
    monkeypatch.setattr(native_router, "execute_channel_query", lambda **kwargs: ([], {"status": "CONFIG_REQUIRED"}))
    import pytest
    with pytest.raises(AcquisitionOutcomeError) as err:
        service.registry.get_channel("sec_edgar").search("AAPL")
    assert err.value.status == "CONFIG_REQUIRED"
