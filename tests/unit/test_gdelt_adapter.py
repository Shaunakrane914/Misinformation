"""Unit tests for GDELT DOC API discovery adapter."""
import json
from unittest.mock import MagicMock, patch

from backend.infrastructure.acquisition.adapters.news.gdelt import GdeltDocAdapter, parse_gdelt_timestamp
from backend.infrastructure.acquisition.adapters.expanded_catalog import get_expanded_adapters, DOMAIN_DISCOVERY, expanded_query
from backend.infrastructure.acquisition.network.http import BoundedHTTPResponse
from backend.services.agent_reach.channels import CandidateSource, RetrievalRequest
from backend.services.research.research_models import ResearchRequest


def test_parse_gdelt_timestamp():
    assert parse_gdelt_timestamp("20261025T123000Z") == "2026-10-25T12:30:00+00:00"
    assert parse_gdelt_timestamp("20261025123000") == "2026-10-25T12:30:00+00:00"
    assert parse_gdelt_timestamp("20261025") == "2026-10-25T00:00:00+00:00"
    assert parse_gdelt_timestamp(None) is None
    assert parse_gdelt_timestamp("invalid") is None


def test_gdelt_adapter_discovery_only_and_acquire_unsupported():
    adapter = GdeltDocAdapter()
    cand_foreign = CandidateSource(url="https://reuters.com/article/battery-recycling-facility")
    assert adapter.can_handle(cand_foreign) is False
    doc_foreign = adapter.acquire(cand_foreign, RetrievalRequest())
    assert doc_foreign.status == "URL_POLICY_REJECTED"

    cand_owned = CandidateSource(url="https://api.gdeltproject.org/api/v2/doc/doc?query=test")
    doc_owned = adapter.acquire(cand_owned, RetrievalRequest())
    assert doc_owned.status == "UNSUPPORTED_DIRECT_ACQUISITION"
    assert "discovery-only" in doc_owned.failure_reason


def test_gdelt_adapter_discover_success():
    adapter = GdeltDocAdapter()
    sample_response = {
        "articles": [
            {
                "url": "https://reuters.com/business/battery-recycling-growth-2026",
                "title": "Battery Recycling Facilities Expand Globally",
                "seendate": "20261025T140000Z",
                "domain": "reuters.com",
                "language": "English",
                "sourcecountry": "United States",
            },
            {
                "url": "https://127.0.0.1/internal-status",  # SSRF candidate - must be excluded
                "title": "Internal Status",
                "seendate": "20261025T140000Z",
                "domain": "internal",
            },
            {
                "url": "https://techcrunch.com/2026/10/25/circular-battery-economy",
                "title": "New Circular Economy Startups in Battery Recycling",
                "seendate": "20261024T180000Z",
                "domain": "techcrunch.com",
                "language": "English",
                "sourcecountry": "United States",
            },
        ]
    }
    mock_resp = BoundedHTTPResponse(
        body=json.dumps(sample_response).encode("utf-8"),
        endpoint="https://api.gdeltproject.org/api/v2/doc/doc",
        status_code=200,
        content_type="application/json",
        headers={},
        latency_ms=120,
        attempts=1,
    )
    def mock_validate(url):
        if "127.0.0.1" in url or "localhost" in url:
            return (False, "SSRF_LOOPBACK")
        return (True, "")

    with patch("backend.infrastructure.acquisition.adapters.news.gdelt.fetch_public_http", return_value=mock_resp), \
         patch("backend.infrastructure.acquisition.adapters.news.gdelt.validate_url_safe", side_effect=mock_validate), \
         patch("backend.infrastructure.acquisition.adapters.expansion_safety.validate_url_safe", side_effect=mock_validate):
        candidates = adapter.discover("battery recycling", limit=5)
        # SSRF localhost was excluded, so 2 remain
        assert len(candidates) == 2
        assert candidates[0].url == "https://reuters.com/business/battery-recycling-growth-2026"
        assert candidates[0].platform == "gdelt"
        assert candidates[0].metadata["discovery_only"] is True
        assert candidates[0].metadata["virality_measured"] is False
        # GDELT's seendate is when GDELT indexed the URL. It is kept as an index observation only.
        assert candidates[0].metadata["gdelt_seen_at"] == "2026-10-25T14:00:00+00:00"
        assert candidates[0].metadata["gdelt_seen_at_raw"] == "20261025T140000Z"
        assert candidates[0].metadata["gdelt_seen_at_basis"] == "GDELT_INDEX_OBSERVATION_NOT_PUBLICATION"
        assert candidates[0].metadata["publication_time_basis"] == "UNKNOWN_UNTIL_PUBLISHER_CONTENT"
        assert "published" not in candidates[0].metadata and "published_at" not in candidates[0].metadata
        assert candidates[1].url == "https://techcrunch.com/2026/10/25/circular-battery-economy"
        assert candidates[1].metadata["gdelt_seen_at"] == "2026-10-24T18:00:00+00:00"


def test_gdelt_adapter_handles_throttling_and_non_200():
    adapter = GdeltDocAdapter()
    mock_resp = BoundedHTTPResponse(
        body=b"Please limit requests to one every 5 seconds",
        endpoint="https://api.gdeltproject.org/api/v2/doc/doc",
        status_code=429,
        content_type="text/plain",
        headers={},
        latency_ms=80,
        attempts=1,
    )
    with patch("backend.infrastructure.acquisition.adapters.news.gdelt.fetch_public_http", return_value=mock_resp):
        candidates = adapter.discover("battery recycling", limit=3)
        assert candidates == []


def test_gdelt_catalog_wiring():
    assert "gdelt" in get_expanded_adapters()
    assert DOMAIN_DISCOVERY["trending"] == "gdelt"
    req = ResearchRequest(target="battery recycling", domain="trending", agent_name="trending")
    q = expanded_query(req)
    assert q is not None
    assert q["channel"] == "expanded_sources"
    assert q["query_text"] == "gdelt|battery recycling"


# ── Provenance: a GDELT first-seen time is never a publication time ──────────────────────────

GDELT_BODY = {
    "articles": [
        {"url": "https://example-publisher.com/news/old-story-reindexed",
         "title": "Battery Recycling Plant Opens", "seendate": "20261025T140000Z",
         "domain": "example-publisher.com", "language": "English", "sourcecountry": "United States"},
        {"url": "https://example-publisher.com/news/odd-date",
         "title": "Battery Recycling Policy Shift", "seendate": "not-a-date",
         "domain": "example-publisher.com", "language": "English", "sourcecountry": "United States"},
    ]
}


def _discover_response():
    return BoundedHTTPResponse(body=json.dumps(GDELT_BODY).encode("utf-8"),
                               endpoint="https://api.gdeltproject.org/api/v2/doc/doc", status_code=200,
                               content_type="application/json", headers={}, latency_ms=50, attempts=1)


def _always_safe(url):
    return (True, "")


def test_gdelt_seen_at_is_not_emitted_as_a_publication_time():
    adapter = GdeltDocAdapter()
    with patch("backend.infrastructure.acquisition.adapters.news.gdelt.fetch_public_http", return_value=_discover_response()), \
         patch("backend.infrastructure.acquisition.adapters.news.gdelt.validate_url_safe", side_effect=_always_safe), \
         patch("backend.infrastructure.acquisition.adapters.expansion_safety.validate_url_safe", side_effect=_always_safe):
        first, second = adapter.discover("battery recycling", limit=5)
    for candidate in (first, second):
        assert "published" not in candidate.metadata and "published_at" not in candidate.metadata
        assert candidate.metadata["publication_time_basis"] == "UNKNOWN_UNTIL_PUBLISHER_CONTENT"
        assert "published" not in candidate.snippet.lower()      # the lead text must not claim a publication date
    assert first.metadata["gdelt_seen_at"] == "2026-10-25T14:00:00+00:00"
    # An unparseable value is preserved verbatim and still invents nothing.
    assert second.metadata["gdelt_seen_at"] is None
    assert second.metadata["gdelt_seen_at_raw"] == "not-a-date"


def _gdelt_fragment():
    from backend.infrastructure.acquisition.adapters.expanded_catalog import ExpandedSourceChannel
    with patch("backend.infrastructure.acquisition.adapters.news.gdelt.fetch_public_http", return_value=_discover_response()), \
         patch("backend.infrastructure.acquisition.adapters.news.gdelt.validate_url_safe", side_effect=_always_safe), \
         patch("backend.infrastructure.acquisition.adapters.expansion_safety.validate_url_safe", side_effect=_always_safe):
        return ExpandedSourceChannel().search("gdelt|battery recycling", limit=3, query_id="expanded_01")[0]


def test_catalog_keeps_first_seen_provenance_without_declaring_publication_time():
    from backend.services.research.research_models import EvidenceItem
    fragment = _gdelt_fragment()
    assert fragment.published == ""                                   # nothing declares a publication time
    meta = fragment.raw_metadata
    assert meta["gdelt_seen_at"] == "2026-10-25T14:00:00+00:00"
    assert meta["gdelt_seen_at_basis"] == "GDELT_INDEX_OBSERVATION_NOT_PUBLICATION"
    assert "published" not in meta and "published_at" not in meta
    assert meta["discovery_only"] is True and meta["linked_article_retrieved"] is False

    item = EvidenceItem.from_evidence_fragment(fragment, "lead_1", "battery recycling")
    assert item.published_at == ""
    assert item.metadata["gdelt_seen_at"] == "2026-10-25T14:00:00+00:00"
    assert item.content_depth == "INDEX_SNIPPET" and item.content == ""


def test_final_publication_gate_ignores_first_seen_freshness():
    """A lead GDELT first saw an hour ago is not fresh evidence until its own captured page says so."""
    from datetime import datetime, timezone
    from backend.services.research.body_context import reconcile_captured_context
    from backend.services.research.research_models import EvidenceItem
    from backend.services.research.temporal_guard import temporal_guard

    reference = datetime(2026, 10, 25, 15, 0, tzinfo=timezone.utc)      # one hour after GDELT "saw" the URL
    fragment = _gdelt_fragment()

    def read_item(page_metadata):
        item = EvidenceItem.from_evidence_fragment(fragment, "lead_1", "battery recycling")
        item.content = "The plant opened after a long permitting process, the operator said in a statement."
        item.metadata.update(read_success=True, temporal_required=True, page_metadata=page_metadata)
        reconcile_captured_context(item)
        return item, temporal_guard.evaluate(item, reference_time=reference)

    # The unread lead has no publication time, whatever GDELT's index says.
    lead = EvidenceItem.from_evidence_fragment(fragment, "lead_0", "battery recycling")
    assessment = temporal_guard.evaluate(lead, reference_time=reference)
    assert (assessment.is_eligible, assessment.status) == (False, "MISSING_TIMESTAMP")

    # Captured page with no publication declaration: still missing, not rescued by gdelt_seen_at.
    item, assessment = read_item({"body_kind": "ARTICLE_BODY"})
    assert item.published_at == ""
    assert (assessment.is_eligible, assessment.status) == (False, "MISSING_TIMESTAMP")
    assert item.metadata["gdelt_seen_at"] == "2026-10-25T14:00:00+00:00"      # provenance survives the read

    # Captured page that declares an old publication date: stale, even though GDELT only just saw it.
    item, assessment = read_item({"body_kind": "ARTICLE_BODY", "published": "2024-03-01T09:00:00+00:00"})
    assert item.published_at == "2024-03-01T09:00:00+00:00"
    assert (assessment.is_eligible, assessment.status) == (False, "STALE")

    # Only the publisher's own declaration inside the 48-hour window makes it eligible.
    item, assessment = read_item({"body_kind": "ARTICLE_BODY", "published": "2026-10-25T08:00:00+00:00"})
    assert assessment.is_eligible is True
    assert item.metadata["publication_time_basis"] == "CAPTURED_PUBLISHER_DECLARATION_UNVERIFIED"
