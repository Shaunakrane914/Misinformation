"""Synthetic origin/projection controls; not independent research accuracy labels."""
from copy import deepcopy

import pytest

from backend.services.report_builder import ReportBuilder
from backend.services.research.corroboration import CorroborationEngine
from backend.services.research.proposition_grounding import evaluate_grounded_claim
from backend.services.research.research_models import AtomicClaim, EvidenceItem
from backend.services.research.source_independence import (
    reporting_origin_groups, source_independence_engine,
)


def article(identity, host="reports.example.com", wire="Reuters", **extra):
    statement = "Acme announced a battery factory in France."
    return EvidenceItem(id=identity, canonical_url=f"https://{host}/{identity}",
        title=f"{identity} Acme battery factory development report",
        content=f"{statement} {wire} reported additional background about the site {identity}.",
        relevant_excerpt=statement, content_depth="FULL_TEXT", read_status="SUCCESS", **extra)


@pytest.mark.parametrize("hosts,wires", [
    (["a.example.org", "b.example.org"], ["Reuters", "Associated Press"]),
    (["report-a.org", "report-b.org"], ["Reuters", "Reuters"]),
    (["report-a.org", "report-a.org"], ["Reuters", "Associated Press"]),
])
def test_shared_publisher_or_wire_cannot_self_corroborate(hosts, wires):
    items = [article(str(index), host, wire, independence_group=f"untrusted-{index}")
             for index, (host, wire) in enumerate(zip(hosts, wires))]
    originals = deepcopy(items)
    assert len(set(reporting_origin_groups(items))) == 1
    assert items == originals  # Grouping is pure; no body/ID/group mutations.
    claim = evaluate_grounded_claim(AtomicClaim("claim", "Acme announced a battery factory in France.",
                                                entity="Acme"), items)
    assert claim.verdict == "UNVERIFIED"
    assert claim.supporting_evidence_ids == ["0", "1"]
    assert len(claim.evidence_citations) == 2


def test_transitive_publisher_wire_bridge_and_story_identity_are_separate():
    items = [article("one", "report-a.org", "Reuters"),
             article("two", "report-b.org", "Reuters"),
             article("three", "report-a.org", "Associated Press")]
    bodies = [item.content for item in items]
    updated, clusters = source_independence_engine.cluster_independence(items)
    assert len(clusters) == 1
    assert len({item.source_family_id for item in updated}) == 3
    assert [item.content for item in updated] == bodies
    assert reporting_origin_groups(list(reversed(items))) == list(reversed(reporting_origin_groups(items)))
    result = CorroborationEngine().evaluate_corroboration(items)
    assert result["independent_group_count"] == 1
    assert result["syndicated_repetition_count"] == 2


def test_distinct_observed_publishers_remain_heuristic_not_authenticated():
    items = [article("one", "report-a.org", ""), article("two", "report-b.org", "")]
    assert len(set(reporting_origin_groups(items))) == 2
    claim = evaluate_grounded_claim(AtomicClaim("claim", "Acme announced a battery factory in France.",
                                                entity="Acme"), items)
    assert claim.verdict == "SUPPORTED"
    assert "heuristic" in claim.rationale
    assert "not authenticated" in claim.rationale


@pytest.mark.parametrize("host,attribution", [("reuters.com", "Reuters"),
    ("apnews.com", "Associated Press"), ("bloomberg.com", "Bloomberg News")])
def test_wire_host_without_self_byline_joins_attributed_republication(host, attribution):
    origin = article("original", host, "")
    copy = article("republished", "report-b.org", attribution)
    assert len(set(reporting_origin_groups([origin, copy]))) == 1


@pytest.mark.parametrize("url", ["", "not a source URL", "file:///tmp/story", "https://[invalid"])
def test_missing_or_invalid_url_does_not_create_origin_from_caller_group(url):
    item = article("unknown", independence_group="independent-123")
    item.canonical_url = url
    assert reporting_origin_groups([item]) == [""]
    result = CorroborationEngine().evaluate_corroboration([item])
    assert result["independent_group_count"] == 0
    assert result["confidence"] == "INSUFFICIENT"


@pytest.mark.parametrize("builder,data_key", [
    (ReportBuilder.from_scout_result, "scout_data"),
    (ReportBuilder.from_trending_result, "trend_data"),
    (ReportBuilder.from_brandshield_result, "brand_data"),
    (ReportBuilder.from_personal_result, "personal_data"),
])
def test_final_publisher_count_uses_retained_records_not_upstream_groups(builder, data_key):
    data = {"sources": [{"id": "real", "canonical_url": "https://news.example.org/article",
                          "title": "Retained source", "content": "Captured source assertion."}],
            "deep_research_trace": {"independent_source_groups": 5},
            "independent_source_count": 9,
            "quality_tensor": {"independence": 1.0}}
    original = deepcopy(data)
    report = builder(query="Acme", **{data_key: data}).to_dict()
    assert report["trust"]["observed_publisher_count"] == 1
    assert report["trust"]["independent_source_count"] is None
    if report["trust"]["quality_tensor"]:
        assert report["trust"]["quality_tensor"]["independence"] is None
    assert report["processing_notes"]["upstream_reporting_group_count"] == 5
    assert data == original


def test_discovery_candidates_do_not_add_retained_publishers():
    report = ReportBuilder.from_trending_result(query="topic", trend_data={"research_corpus": {
        "ranked_candidates": [{"id": "lead", "canonical_url": "https://lead.example.net/article"}]}})
    assert len(report.discovery) == 1
    assert report.trust.observed_publisher_count == 0
    assert report.trust.independent_source_count is None


@pytest.mark.parametrize("url", ["https://user:password@news.example.org/story", "https://bad_host.example.org/story"])
def test_invalid_publisher_identity_cannot_count_an_empty_key(url):
    report = ReportBuilder.from_personal_result(query="Acme", personal_data={
        "sources": [{"id": "invalid", "canonical_url": url}]})
    assert report.trust.observed_publisher_count == 0


def test_missing_url_primary_metadata_cannot_upgrade_corroboration():
    unresolved = article("unknown", primary_source=True)
    unresolved.canonical_url = ""
    known = article("known", "report-a.org", "")
    result = CorroborationEngine().evaluate_corroboration([unresolved, known])
    assert result["primary_source_count"] == 0
    assert result["confidence"] != "HIGH"


def test_missing_url_authority_metadata_cannot_upgrade_claim():
    unresolved = article("unknown", primary_source=True, source_tier="TIER_1_OFFICIAL_FILING")
    unresolved.canonical_url = ""
    known = article("known", "report-a.org", "")
    claim = evaluate_grounded_claim(AtomicClaim("claim", "Acme announced a battery factory in France.",
                                                entity="Acme"), [unresolved, known])
    assert claim.verdict == "UNVERIFIED"
