"""Development controls, not a claim-accuracy benchmark."""
import hashlib

import pytest

from backend.schemas.evidence_inspection import inspect_evidence, summarize_inspections
from backend.services.agent_reach.channels import EvidenceFragment
from backend.schemas.unified_report import UnifiedEvidenceItem
from backend.services.report_builder import _dict_to_evidence_item


OPERATIONS = (
    "github.read github.issues github.prs github.commits github.releases "
    "youtube.read youtube.transcript youtube.comments v2ex.latest v2ex.search "
    "v2ex.topic v2ex.replies web.read rss.read xiaoyuzhou.podcast xiaoyuzhou.episodes "
    "reddit.read reddit.comments twitter.status twitter.profile hackernews.read stackexchange.read"
).split()


@pytest.mark.parametrize("operation", OPERATIONS)
def test_exact_capture_and_missing_fields_for_all_operations(operation):
    body = "Observed sentence, not a verified finding.\n" * 30
    item = EvidenceFragment(platform=operation.split('.')[0], content=body, content_depth="PARTIAL_CONTENT")
    result = inspect_evidence(item)
    assert result["captured_text_sha256"] == hashlib.sha256(body.encode()).hexdigest()
    assert {"url", "title", "author", "published_at"} <= set(result["missing_fields"])
    assert result["source_completeness"] == "UNKNOWN"
    assert result["support_assessment"] == "NOT_ASSESSED"
    for passage in result["passages"]:
        assert body[passage["start"]:passage["end"]] == passage["text"]


def test_passages_are_stable_bounded_query_selected_and_not_truth():
    item = {"url": "https://example.org/article", "content": "x" * 6000 + " revenue disclosure" * 500,
            "query_text": "revenue disclosure", "content_depth": "METADATA"}
    result = inspect_evidence(item)
    assert result == inspect_evidence(item)
    assert len(result["passages"]) == 8
    assert any("revenue disclosure" in passage["text"] for passage in result["passages"])
    assert result["evidentiary_use"] == "DISCOVERY_ONLY"
    assert result["passages_omitted"] > 0
    item["content"] += " changed"
    assert inspect_evidence(item)["document_id"] != result["document_id"]


def test_inspection_cap_unicode_and_no_source_mutation():
    item = {"content": "नमस्ते" * 20000, "raw_metadata": {"truncated": True}}
    result = inspect_evidence(item)
    assert result["inspection_truncated"] is True
    assert result["provider_truncated"] is True
    assert result["inspected_chars"] == 100000
    assert len(item["content"]) == 120000
    assert "extraction" not in item


def test_reports_recompute_capture_instead_of_trusting_stale_metadata():
    item = {"content": "Actual captured body", "title": "Observed", "extraction": {"claim_accuracy": 1}}
    serialized = _dict_to_evidence_item(item).to_dict()
    assert serialized["extraction"]["passages"][0]["text"] == item["content"]
    assert "claim_accuracy" not in serialized["extraction"]
    fragment = EvidenceFragment(platform="reddit", content="Public thread", content_depth="SOCIAL_POST")
    assert UnifiedEvidenceItem.from_evidence_item(fragment).to_dict()["extraction"]["captured_chars"] == 13
    assert summarize_inspections([])["claim_accuracy"] is None


def test_unknown_content_depth_does_not_become_body_evidence():
    assert inspect_evidence({"snippet": "Search index text"})["evidentiary_use"] == "DISCOVERY_ONLY"
    assert inspect_evidence({"content_depth": "DIRECT_METADATA", "content": "Filing index"})["evidentiary_use"] == "DISCOVERY_ONLY"


def test_structured_observations_are_bounded_and_numeric_mentions_are_exact():
    body = "Revenue was $12.5 billion in 2025; this is an observed quote, not a verified fact."
    result = inspect_evidence({"content": body, "metadata": {"content_depth": "PARTIAL_CONTENT", "page_metadata": {
        "tables": [[["A" * 500, "Value"]]], "quotations": ["Quote"], "potential_corrections": ["Correction notice"],
    }}})
    assert result["content_depth"] == "PARTIAL_CONTENT"
    assert len(result["page_observations"]["tables"][0][0][0]) == 120
    assert result["observed_numeric_mentions"][0]["text"] == "$12.5 billion"
    for mention in result["observed_numeric_mentions"]:
        assert body[mention["start"]:mention["end"]] == mention["text"]
    assert result["support_assessment"] == "NOT_ASSESSED"


def test_x_missing_engagement_and_identity_are_not_fabricated():
    from backend.services.agent_reach.native.normalizer import NativeNormalizer
    profile = NativeNormalizer.normalize_fxtwitter_profile({"screen_name": "example"})
    assert profile.raw_metadata["followers"] is None
    assert profile.raw_metadata["tweets_count"] is None
    assert profile.content == ""
    assert profile.content_depth == "PROFILE_METADATA"
    assert NativeNormalizer.normalize_fxtwitter_profile({"name": "No handle"}) is None
    dated = NativeNormalizer.normalize_fxtwitter_profile({"screen_name": "example", "joined": "2007-01-01"})
    assert dated.published == ""
    assert dated.raw_metadata["account_created_at"] == "2007-01-01"


def test_personal_normalization_preserves_depth_and_missing_counts():
    from backend.agents.personal_watch.monitoring import normalize_item
    result = normalize_item({"title": "Profile", "url": "https://x.com/example", "metadata": {
        "content_depth": "PROFILE_METADATA", "query_id": "q1", "secret_cookie": "never forward",
    }}, "twitter", "COMMUNITY", "Subject")
    assert result["content_depth"] == "PROFILE_METADATA"
    assert result["metadata"]["query_id"] == "q1"
    assert result["metadata"]["likes"] is None
    assert result["author"] == ""
    assert "secret_cookie" not in result["metadata"]


def test_personal_evidence_survives_report_and_generic_brand_records_are_not_primary():
    from backend.services.report_builder import ReportBuilder
    record = {"title": "Observed public mention", "content": "Captured context", "platform": "reddit",
              "url": "https://www.reddit.com/r/test/comments/abc/", "source_role": "COMMUNITY"}
    personal = ReportBuilder.from_personal_result(query="Subject", personal_data={"evidence": [record]}).to_dict()
    assert len(personal["evidence"]["community"]) == 1
    assert personal["evidence"]["community"][0]["extraction"]["passages"][0]["text"] == record["content"]
    brand = ReportBuilder.from_brandshield_result(query="Brand", brand_data={"evidence": [record]}).to_dict()
    assert not brand["evidence"]["primary"]
    assert len(brand["evidence"]["community"]) == 1


@pytest.mark.parametrize("reported_depth", ["PROFILE_METADATA", "VIDEO_METADATA", "DIRECT_METADATA", None])
def test_deep_read_never_promotes_metadata_or_length_to_full_article(monkeypatch, reported_depth):
    from backend.services.research.deep_reader import DeepReader
    from backend.services.research.research_models import EvidenceItem
    item = EvidenceItem(id="observed", canonical_url="https://example.org/source", content_depth="SNIPPET")
    monkeypatch.setattr("backend.services.agent_reach.agent_reach_service.read", lambda *args, **kwargs: {
        "status": "success", "markdown": "Captured context. " * 100, "content_depth": reported_depth,
    })
    inspected, telemetry = DeepReader().deep_read([item], max_reads=1, timeout_per_read=2)
    assert len(inspected) == 1 and telemetry["successful"] == 1
    assert inspected[0].content_depth == (reported_depth or "PARTIAL_CONTENT")
    assert inspected[0].content_depth != "FULL_ARTICLE"
