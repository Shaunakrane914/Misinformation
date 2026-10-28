"""Synthetic offline CPSC-schema responses; no genuine/live recall evidence.

These fixtures model published RecallID/Title/URL/RecallDate/Description,
Hazards[].Name and Remedies[].Name fields. They are not downloaded records.
"""

from copy import deepcopy
import json
from unittest.mock import MagicMock
from urllib.parse import parse_qs, urlsplit

import pytest

from backend.infrastructure.acquisition.adapters import expansion_safety
from backend.infrastructure.acquisition.adapters.consumer import cpsc_recalls as cpsc
from backend.infrastructure.acquisition.network.http import BoundedHTTPResponse
from backend.services.agent_reach.channels import CandidateSource, FetchedDocument, RetrievalRequest


@pytest.fixture(autouse=True)
def no_outbound_transport(monkeypatch):
    monkeypatch.setattr(expansion_safety, "_fetch", MagicMock(side_effect=AssertionError("Offline fixture only")))
    monkeypatch.setattr(expansion_safety, "validate_url_safe", lambda _: (False, "Offline fixture only"))


@pytest.fixture
def synthetic_record():
    return {"RecallID": 12345, "RecallNumber": "26999",
            "Title": "Synthetic Example recalls test lamps due to fire hazard",
            "URL": "http://www.cpsc.gov/Recalls/2026/Synthetic-Example-Test-Lamp-Recall/",
            "RecallDate": "2026-10-01T00:00:00", "LastPublishDate": "2026-10-02T09:01:02",
            "Description": "Synthetic fixture: model TEST-100.  Preserve exact spacing.\nSecond line.",
            "Hazards": [{"Name": "Synthetic fixture: the cord can overheat.", "HazardType": "Fire"}],
            "Remedies": [{"Name": "Synthetic fixture: stop use and request a refund."}],
            "Products": [{"Name": "Synthetic test lamps", "Model": "TEST-100"}],
            "Images": [{"URL": "https://www.cpsc.gov/synthetic-fixture.jpg"}]}


def mock_response(records, url, *, status=200, content_type="application/json; charset=utf-8"):
    return BoundedHTTPResponse(body=json.dumps(records).encode(), endpoint=url, status_code=status,
                               content_type=content_type, headers={}, latency_ms=1, attempts=1)


def install_response(monkeypatch, records, **kwargs):
    fetch = MagicMock(side_effect=lambda url, **_: mock_response(records, url, **kwargs))
    monkeypatch.setattr(cpsc, "safe_fetch", fetch)
    return fetch


def test_discovery_caps_results_and_encodes_only_documented_query(monkeypatch, synthetic_record):
    records = []
    for index in range(8):
        record = deepcopy(synthetic_record)
        record["RecallID"] += index
        record["URL"] = record["URL"].rstrip("/") + f"-{index}"
        records.append(record)
    fetch = install_response(monkeypatch, records)
    results = cpsc.CpscRecallsAdapter().discover("Test & format=xml", limit=1000)
    assert len(results) == 5
    fetch.assert_called_once()
    url, = fetch.call_args.args
    assert urlsplit(url)._replace(query="").geturl() == cpsc.CPSC_API_URL
    assert parse_qs(urlsplit(url).query) == {"format": ["json"], "RecallTitle": ["Test & format=xml"]}
    assert fetch.call_args.kwargs["timeout"] == 5.0
    assert fetch.call_args.kwargs["max_bytes"] == 1_000_000
    assert fetch.call_args.kwargs["max_redirects"] == 0
    assert results[0].metadata["discovery_only"] is True


def test_observed_record_survives_acquisition_and_normalization(monkeypatch, synthetic_record):
    fetch = install_response(monkeypatch, [synthetic_record])
    adapter = cpsc.CpscRecallsAdapter()
    candidate, = adapter.discover("Synthetic Example")
    document = adapter.acquire(candidate, RetrievalRequest(task_type="READ"))
    fragment, = adapter.normalize(document, candidate, RetrievalRequest())
    fetch.assert_called_once()  # No unbudgeted detail/page fetch.
    assert document.status == "SUCCESS"
    assert json.loads(document.raw_content) == synthetic_record
    assert fragment.title == synthetic_record["Title"]
    assert fragment.url == "https://www.cpsc.gov/Recalls/2026/Synthetic-Example-Test-Lamp-Recall"
    assert fragment.published == synthetic_record["RecallDate"]
    assert fragment.content_depth == "STRUCTURED_EVIDENCE"
    assert fragment.retrieval_mode == "direct_api"
    assert fragment.raw_metadata["original_record"] == synthetic_record
    assert fragment.raw_metadata["RecallID"] == synthetic_record["RecallID"]
    assert fragment.raw_metadata["description"] == synthetic_record["Description"]
    assert fragment.raw_metadata["hazards"] == [synthetic_record["Hazards"][0]["Name"]]
    assert fragment.raw_metadata["remedies"] == [synthetic_record["Remedies"][0]["Name"]]
    assert fragment.raw_metadata["field_provenance"]["description"] == "/0/Description"
    assert fragment.raw_metadata["source_role"] == "ISSUING_AGENCY"
    assert fragment.raw_metadata["source_assertion_only"] is True
    assert fragment.raw_metadata["article_body_acquired"] is False
    assert "adjudicated" not in fragment.content.lower()
    synthetic_record["Description"] = "Changed fixture after normalization"
    assert fragment.raw_metadata["description"] != synthetic_record["Description"]


@pytest.mark.parametrize("url", [
    "https://www.cpsc.gov.attacker.invalid/Recalls/2026/test", "https://attacker.invalid/cpsc.gov/Recalls/2026/test",
    "https://user:password@www.cpsc.gov/Recalls/2026/test", "file:///cpsc.gov/Recalls/2026/test",
    "https://www.cpsc.gov/Recalls", "https://www.cpsc.gov:8443/Recalls/2026/test",
])
def test_forged_platform_or_listing_is_not_owned(url):
    assert not cpsc.CpscRecallsAdapter().can_handle(CandidateSource(url=url, platform="cpsc_recalls"))


def test_webpage_or_id_only_candidate_has_no_inferred_api_body(monkeypatch):
    fetch = MagicMock(side_effect=AssertionError("No fetch is allowed"))
    monkeypatch.setattr(cpsc, "safe_fetch", fetch)
    adapter = cpsc.CpscRecallsAdapter()
    candidate = CandidateSource(url="https://www.cpsc.gov/Recalls/2026/test", metadata={"RecallID": 12345})
    document = adapter.acquire(candidate, RetrievalRequest())
    assert document.status == "NO_ELIGIBLE_API_RECORD"
    assert adapter.normalize(document, candidate, RetrievalRequest()) == []
    fetch.assert_not_called()


def test_matching_record_and_fixed_api_provenance_are_required(monkeypatch, synthetic_record):
    install_response(monkeypatch, [synthetic_record])
    adapter = cpsc.CpscRecallsAdapter()
    candidate, = adapter.discover("Synthetic")
    candidate.metadata["api_url"] = "https://attacker.invalid/RestWebServices/Recall?format=json&RecallTitle=Synthetic"
    assert adapter.acquire(candidate, RetrievalRequest()).status == "NO_ELIGIBLE_API_RECORD"
    candidate.metadata["api_url"] = cpsc.CPSC_API_URL + "?format=json&RecallTitle=Synthetic"
    candidate.url = candidate.canonical_url = "https://www.cpsc.gov/Recalls/2026/another-record"
    assert adapter.acquire(candidate, RetrievalRequest()).status == "NO_ELIGIBLE_API_RECORD"


@pytest.mark.parametrize("records", [{"results": []}, [None], [{"RecallID": True}], []])
def test_invalid_or_empty_schema_is_not_positive_evidence(monkeypatch, records):
    fetch = install_response(monkeypatch, records)
    assert cpsc.CpscRecallsAdapter().discover("Synthetic") == []
    fetch.assert_called_once()


@pytest.mark.parametrize("status,content_type", [(429, "application/json"), (403, "application/json"), (200, "text/html")])
def test_denied_or_non_json_response_has_no_retry(monkeypatch, synthetic_record, status, content_type):
    fetch = install_response(monkeypatch, [synthetic_record], status=status, content_type=content_type)
    assert cpsc.CpscRecallsAdapter().discover("Synthetic") == []
    fetch.assert_called_once()


@pytest.mark.parametrize("body", [b"[invalid JSON", b" " * 1_000_001], ids=["invalid_json", "oversized"])
def test_invalid_or_oversized_body_is_rejected(monkeypatch, body):
    fetch = MagicMock(side_effect=lambda url, **_: BoundedHTTPResponse(
        body=body, endpoint=url, status_code=200, content_type="application/json", headers={}, latency_ms=1, attempts=1))
    monkeypatch.setattr(cpsc, "safe_fetch", fetch)
    assert cpsc.CpscRecallsAdapter().discover("Synthetic") == []
    fetch.assert_called_once()


def test_transport_policy_rejection_precedes_any_http_call():
    assert cpsc.CpscRecallsAdapter().discover("Synthetic") == []
    expansion_safety._fetch.assert_not_called()


def test_real_safety_wrapper_keeps_single_attempt_and_response_budgets(monkeypatch, synthetic_record):
    monkeypatch.setattr(expansion_safety, "validate_url_safe", lambda _: (True, "Synthetic allowlist fixture"))
    fetch = MagicMock(side_effect=lambda url, **_: mock_response([synthetic_record], url))
    monkeypatch.setattr(expansion_safety, "_fetch", fetch)
    assert len(cpsc.CpscRecallsAdapter().discover("Synthetic")) == 1
    fetch.assert_called_once()
    assert {key: fetch.call_args.kwargs[key] for key in ("timeout", "max_bytes", "max_attempts", "max_redirects")} == {
        "timeout": 5.0, "max_bytes": 1_000_000, "max_attempts": 1, "max_redirects": 0}


def test_truncated_display_retains_complete_original_fields(monkeypatch, synthetic_record):
    synthetic_record["Description"] = "Synthetic long description. " * 1500
    install_response(monkeypatch, [synthetic_record])
    adapter = cpsc.CpscRecallsAdapter()
    candidate, = adapter.discover("Synthetic")
    document = adapter.acquire(candidate, RetrievalRequest())
    fragment, = adapter.normalize(document, candidate, RetrievalRequest())
    assert len(fragment.content) == 25_000
    assert fragment.raw_metadata["truncated"] is True
    assert fragment.raw_metadata["description"] == synthetic_record["Description"]
    assert fragment.raw_metadata["original_record"]["Description"] == synthetic_record["Description"]


def test_unsuccessful_or_wrong_document_cannot_normalize():
    candidate = CandidateSource(url="https://www.cpsc.gov/Recalls/2026/test")
    adapter = cpsc.CpscRecallsAdapter()
    assert adapter.normalize(FetchedDocument(url=candidate.url, status="FAILED"), candidate, RetrievalRequest()) == []
    assert adapter.health()["live_health_verified"] is False


def test_registered_expanded_cpsc_discovery_preserves_index_provenance_only(monkeypatch, synthetic_record):
    from backend.infrastructure.acquisition.adapters import expanded_catalog
    assert expanded_catalog.ADAPTERS['cpsc_recalls'] == ('consumer.cpsc_recalls', 'CpscRecallsAdapter')
    fetch = install_response(monkeypatch, [synthetic_record])
    monkeypatch.setattr(expanded_catalog, 'get_expanded_adapters',
                        lambda: {'cpsc_recalls': cpsc.CpscRecallsAdapter()})
    fragment, = expanded_catalog.ExpandedSourceChannel().search('cpsc_recalls|Synthetic Example')
    fetch.assert_called_once()
    assert fragment.content == ''
    assert fragment.content_depth == 'INDEX_SNIPPET'
    assert not fragment.published
    assert fragment.raw_metadata['cpsc_recall_id'] == synthetic_record['RecallID']
    assert fragment.raw_metadata['cpsc_record_index'] == 0
    assert fragment.raw_metadata['cpsc_issue_date'] == synthetic_record['RecallDate']
    assert fragment.raw_metadata['cpsc_api_url'].startswith(cpsc.CPSC_API_URL + '?')
    assert fragment.raw_metadata['discovery_only'] is True
    assert fragment.raw_metadata['linked_article_retrieved'] is False
    assert fragment.raw_metadata['primary_source'] is False
    assert 'cpsc_record' not in fragment.raw_metadata
    assert 'published' not in fragment.raw_metadata and 'published_at' not in fragment.raw_metadata


def test_generic_expanded_reader_leaves_cpsc_html_to_ordinary_reader(monkeypatch):
    from backend.infrastructure.acquisition.adapters import expanded_catalog
    adapter = cpsc.CpscRecallsAdapter()
    adapter.can_handle = MagicMock(side_effect=AssertionError('CPSC discovery cannot intercept the webpage reader'))
    adapter.acquire = MagicMock(side_effect=AssertionError('No API body may be inferred from a webpage URL'))
    monkeypatch.setattr(expanded_catalog, 'get_expanded_adapters', lambda: {'cpsc_recalls': adapter})
    assert expanded_catalog.read_expanded_url('https://www.cpsc.gov/Recalls/2026/observed-recall') is None
    adapter.can_handle.assert_not_called()
    adapter.acquire.assert_not_called()


def test_dns_timeout_keeps_empty_discovery_and_explicit_preflight_failure(monkeypatch):
    monkeypatch.setattr(expansion_safety, 'validate_url_safe', lambda _: (False, 'DNS validation timed out'))
    with expansion_safety.capture_adapter_fetches() as observations:
        assert cpsc.CpscRecallsAdapter().discover('Synthetic Example') == []
    assert observations == [{'failure_type': 'DNS_TIMEOUT', 'stage': 'URL_VALIDATION',
                             'network_observed': False}]
    expansion_safety._fetch.assert_not_called()


def test_direct_api_cannot_ignore_missing_source_review(monkeypatch):
    from backend.services.research import source_registry as policy
    monkeypatch.setattr(policy, 'source_registry', policy.SourceRegistry(reviews={}))
    fetch = MagicMock(side_effect=AssertionError('Unreviewed API must not be fetched'))
    monkeypatch.setattr(cpsc, 'safe_fetch', fetch)
    assert cpsc.CpscRecallsAdapter().discover('Synthetic battery') == []
    fetch.assert_not_called()


def test_api_only_review_is_not_advertised_as_automatic_web_article_route():
    from backend.services.research.source_registry import SourceRegistry
    from backend.services.research.topic_context import infer_context
    policy = SourceRegistry()
    context = infer_context('Cedar Tools product recall', 'Cedar Tools', agent='brandshield')
    selected, decisions = policy.select(context)
    assert 'cpsc' not in {row['id'] for row in selected}
    decision = next(row for row in decisions if row['source_family'] == 'cpsc')
    assert decision['routing_reason'] == 'EXPLICIT_ADAPTER_ONLY'
