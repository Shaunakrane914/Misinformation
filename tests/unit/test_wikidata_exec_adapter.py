"""Unit tests for WikidataExecutiveAdapter."""

import json
from unittest.mock import patch

from backend.infrastructure.acquisition.adapters.governance.wikidata_exec import WikidataExecutiveAdapter
from backend.infrastructure.acquisition.network.http import BoundedHTTPResponse
from backend.services.agent_reach.channels import (
    CandidateSource,
    FetchedDocument,
    RetrievalRequest,
)


def test_wikidata_exec_adapter_can_handle():
    adapter = WikidataExecutiveAdapter()
    assert adapter.can_handle(CandidateSource(url="https://www.wikidata.org/wiki/Q318043")) is True
    assert adapter.can_handle(CandidateSource(url="https://www.opensanctions.org/entities/Q318043")) is False
    assert adapter.can_handle(CandidateSource(url="https://example.com/other", platform="wikidata_exec")) is False
    assert adapter.can_handle(CandidateSource(url="https://example.com/other")) is False


def test_wikidata_exec_adapter_discover():
    adapter = WikidataExecutiveAdapter()
    sample_search = {
        "search": [
            {
                "id": "Q318043",
                "label": "Jensen Huang",
                "description": "Taiwanese-American businessman and electrical engineer, CEO of Nvidia",
                "concepturi": "http://www.wikidata.org/entity/Q318043",
            }
        ]
    }
    mock_resp = BoundedHTTPResponse(
        body=json.dumps(sample_search).encode("utf-8"),
        endpoint="https://www.wikidata.org/w/api.php?action=wbsearchentities",
        status_code=200,
        content_type="application/json",
        headers={},
        latency_ms=45,
        attempts=1,
    )

    with patch("backend.infrastructure.acquisition.adapters.governance.wikidata_exec.fetch_public_http", return_value=mock_resp):
        candidates = adapter.discover("Jensen Huang", limit=1)
        assert len(candidates) == 1
        c = candidates[0]
        assert c.platform == "wikidata_exec"
        assert "Jensen Huang" in c.title
        assert c.metadata["qid"] == "Q318043"


def test_wikidata_exec_adapter_acquire_and_normalize():
    adapter = WikidataExecutiveAdapter()
    sample_entity = {
        "entities": {
            "Q318043": {
                "id": "Q318043",
                "labels": {"en": {"value": "Jensen Huang"}},
                "descriptions": {"en": {"value": "CEO and co-founder of Nvidia"}},
                "aliases": {"en": [{"value": "Jen-Hsun Huang"}]},
                "claims": {
                    "P106": [{"id": "c1"}, {"id": "c2"}],
                    "P108": [{"id": "c3"}],
                    "P39": [{"id": "c4"}],
                    "P569": [{"id": "c5"}],
                },
            }
        }
    }
    mock_resp = BoundedHTTPResponse(
        body=json.dumps(sample_entity).encode("utf-8"),
        endpoint="https://www.wikidata.org/wiki/Special:EntityData/Q318043.json",
        status_code=200,
        content_type="application/json",
        headers={},
        latency_ms=50,
        attempts=1,
    )

    cand = CandidateSource(
        url="https://www.wikidata.org/wiki/Q318043",
        platform="wikidata_exec",
        title="Jensen Huang — Wikidata",
        metadata={"qid": "Q318043"},
    )

    with patch("backend.infrastructure.acquisition.adapters.governance.wikidata_exec.fetch_public_http", return_value=mock_resp):
        doc = adapter.acquire(cand, RetrievalRequest())
        assert doc.status == "SUCCESS"
        assert "Jen-Hsun Huang" in doc.raw_content
        assert "Occupation (P106)" in doc.raw_content
        assert "Employer / Corporate Ties (P108)" in doc.raw_content

        frags = adapter.normalize(doc, cand, RetrievalRequest())
        assert len(frags) == 1
        frag = frags[0]
        assert frag.platform == "wikidata_exec"
        assert "Jen-Hsun Huang" in frag.content
        assert frag.raw_metadata["source_domain"] == "wikidata.org"
