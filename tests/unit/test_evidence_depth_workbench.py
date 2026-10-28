"""Synthetic/offline controls. Passage capacity is not live source recall."""
import copy
import hashlib
from collections import Counter

import pytest

from backend.schemas.evidence_inspection import inspect_evidence, public_capture_metadata
from backend.services.research.evidence_workbench import build_evidence_workbench
from backend.services.research.harvesting import _read_priority, diversified_queries
from backend.services.research.passage_extractor import PassageExtractor
from backend.services.research.research_models import EvidenceItem
from backend.services.research.source_diversity import SOURCE_FAMILIES, diversify_search_plan


def source(body=None, **changes):
    body = body or "\n\n".join(f"Quartz Tools reported revenue of USD {index + 1} million in operating division {index}. The statement has not been independently audited."
                             for index in range(25))
    item = EvidenceItem(id="ev_quartz", canonical_url="https://publisher.example/results", content=body,
                        title="Quartz Tools results", content_depth="DEEP_READ", acquired_id="capture1",
                        metadata={"layer2_eligible": True, "page_metadata": {"body_kind": "ARTICLE_BODY"}})
    for key, value in changes.items():
        setattr(item, key, value)
    return item


def extract(item, domain="financial", target="Quartz Tools"):
    return PassageExtractor().extract_passages([item], target_name=target, domain=domain)[0]


def public(item):
    return {"evidence_id": item.id, "url": item.canonical_url, "title": item.title,
            "extraction": inspect_evidence(item)}


def test_twentyfold_synthetic_publication_capacity_without_extra_findings_or_calls():
    item = source()
    original = item.content
    extract(item)
    workbench = build_evidence_workbench([public(item)])
    assert len(workbench["passages"]) == 25
    assert workbench["accounting"]["published_unique_words"] >= 20 * len(item.relevant_excerpt.split())
    assert item.content == original
    assert workbench["target_status"] == "NOT_EVALUATED"
    for row in workbench["passages"]:
        assert original[row["start"]:row["end"]] == row["text"]
        assert row["captured_text_sha256"] == hashlib.sha256(original.encode()).hexdigest()
        assert "not been independently audited" in row["text"]
        assert row["claim_status"] == "UNVERIFIED"


@pytest.mark.parametrize("changes", [
    {"content_depth": "SNIPPET"}, {"metadata": {"layer2_eligible": False}},
    {"metadata": {"content_role": "PROFILE"}},
    {"metadata": {"temporal_required": True, "temporal_eligible": False}},
])
def test_unqualified_records_do_not_gain_workbench_passages(changes):
    item = source(**changes)
    extract(item)
    assert not build_evidence_workbench([public(item)])["passages"]


def test_stale_stored_projection_is_cleared_after_body_requalification():
    item = extract(source())
    assert item.metadata["evidence_passages"]
    item.content = "Shop all products. Toggle navigation. Privacy policy."
    extract(item)
    assert not item.metadata.get("evidence_passages")


@pytest.mark.parametrize("mutation", ["body", "hash", "offset", "identity", "discovery"])
def test_inspection_and_workbench_reject_invalid_projections(mutation):
    item = extract(source())
    if mutation == "body":
        item.content += " changed"
    elif mutation == "hash":
        for row in item.metadata["evidence_passages"]:
            row["captured_text_sha256"] = "wrong"
    elif mutation == "offset":
        for row in item.metadata["evidence_passages"]:
            row["start"] += 1
    data = public(item)
    if mutation == "identity":
        data["evidence_id"] = "another-source"
    elif mutation == "discovery":
        data["extraction"]["evidentiary_use"] = "DISCOVERY_ONLY"
    assert not build_evidence_workbench([data])["passages"]


def test_native_metadata_roundtrip_preserves_exact_passages_and_no_input_mutation():
    item = extract(source())
    before = copy.deepcopy(item.to_dict())
    metadata = public_capture_metadata(item)
    restored = source(metadata=metadata)
    assert inspect_evidence(restored)["evidence_passages"] == inspect_evidence(item)["evidence_passages"]
    assert item.to_dict() == before
    assert public_capture_metadata(item, max_chars=100)["evidence_passages"] == []


def test_duplicate_text_does_not_count_as_extra_words_or_independence():
    first = extract(source())
    second = extract(source(id="ev_second", canonical_url="https://other.example/result"))
    result = build_evidence_workbench([public(first), public(second)])
    assert result["accounting"]["identical_text_observations"] == 25
    assert result["accounting"]["published_passages"] == 25
    assert result["accounting"]["independence_verified"] is False
    assert all(row["also_reported_by"][0]["evidence_id"] == "ev_second" for row in result["passages"])


def test_workbench_has_explicit_budgets_and_source_fairness(monkeypatch):
    import backend.services.research.evidence_workbench as module
    first = extract(source())
    second = extract(source(body=first.content.replace("operating", "research"), id="ev_second"))
    monkeypatch.setattr(module, "MAX_WORKBENCH_PASSAGES", 2)
    result = module.build_evidence_workbench([public(first), public(second)])
    assert {row["evidence_id"] for row in result["passages"]} == {first.id, second.id}
    assert result["accounting"]["omitted_by_workbench_budget"] == 48
    assert result["accounting"]["published_text_utf8_bytes"] <= result["limits"]["max_text_utf8_bytes"]


def test_source_budget_and_complete_paragraphs_are_explicit():
    item = extract(source(body="\n\n".join(
        f"Quartz Tools reported revenue of USD {index} million. " + "The report has limitations. " * 8
        for index in range(100))))
    accounting = item.metadata["evidence_passage_accounting"]
    assert accounting["omitted_by_source_budget"] > 0
    assert sum(len(row["text"]) for row in item.metadata["evidence_passages"]) <= 20_000
    assert all(row["text"].endswith("limitations.") for row in item.metadata["evidence_passages"])


@pytest.mark.parametrize("domain", ["financial", "trending", "brand", "personal"])
def test_all_agent_plans_include_bounded_different_publisher_families(domain):
    original = diversified_queries("Quartz Tools", domain)
    before = copy.deepcopy(original)
    rows = diversify_search_plan(original, "Quartz Tools", domain, 12)
    scoped = [row for row in rows if row.get("source_family")]
    expected = 1 if domain in {'trending', 'personal'} else 3
    assert len(rows) == 12 and len(scoped) == expected
    if domain in {'trending', 'personal'}:
        assert {row['source_family'] for row in scoped} == {'general_reporting'}
    assert len({host for row in scoped for host in SOURCE_FAMILIES[row["source_family"]]}) == expected * 3
    assert all(row["channel"] == "web" and "Quartz Tools" in row["query_text"] for row in scoped)
    assert original == before
    assert not any("reddit.com" in row["query_text"] or "sec.gov" in row["query_text"] for row in scoped)


def test_validated_tasks_and_temporal_hints_survive_diversification():
    original = diversified_queries("Elena Rivera", "personal", specialist_tasks=["FALSE_QUOTE"])
    original[0]["source_plan_action_id"] = "validated"
    rows = diversify_search_plan(original, "Elena Rivera", "personal", 9)
    assert rows[0]["source_plan_action_id"] == "validated"
    assert all(row["specialist_task"] == "FALSE_QUOTE" for row in rows)
    assert all("source_plan_action_id" not in row for row in rows if row.get("source_family"))
    trend = diversify_search_plan(diversified_queries("battery storage", "trending"), "battery storage", "trending", 12)
    assert all("when:2d after:" in row["query_text"] for row in trend)


@pytest.mark.parametrize("limit", [1, 2, 5, 6, 12, 18])
def test_diversification_never_increases_query_budget(limit):
    assert len(diversify_search_plan(diversified_queries("Quartz Tools", "brand"), "Quartz Tools", "brand", limit)) <= limit


def test_explicit_site_scope_is_not_overwritten():
    rows = [{"channel": "web", "query_text": f"Quartz site:publisher.example item {index}"} for index in range(12)]
    assert diversify_search_plan(rows, "Quartz", "brand", 12) == rows


def test_scoped_discovery_receives_an_early_bounded_opportunity():
    rows = diversify_search_plan(diversified_queries("Quartz", "financial"), "Quartz", "financial", 12)
    assert rows[2].get("source_family")


def test_publisher_monopoly_does_not_fill_entire_candidate_pool():
    from backend.services.research.harvesting import HarvestingEngine
    from backend.services.research.research_profiles import QUICK
    from dataclasses import replace
    from backend.services.agent_reach.channels import RetrievalResult
    class Service:
        def retrieve_many(self, *args, **kwargs):
            return RetrievalResult(query="Quartz", domain="financial")
    class Reader:
        def deep_read(self, *args, **kwargs):
            return [], {"attempted": 0}
    leads = [EvidenceItem(id=str(index), canonical_url=f"https://same.example/article/{index}",
             title="Quartz reported quarterly revenue") for index in range(18)]
    leads.append(EvidenceItem(id="other", canonical_url="https://other.example/article", title=leads[0].title))
    result = HarvestingEngine(Service(), Reader()).run("Quartz", "financial", initial_candidates=leads,
        profile=replace(QUICK, max_queries=1))
    assert any(item.canonical_url.startswith("https://other.example") for item in result.candidates)
    assert result.metrics["discarded_by_reason"]["PUBLISHER_DISCOVERY_SHARE_LIMIT"] > 0
    assert len(result.candidates) < QUICK.max_candidates
    assert not result.captures


def test_financial_context_and_corrections_remain_separate_from_findings():
    item = extract(source(body='Quartz Tools reported revenue of USD 12 million, but expects lower earnings next quarter.'))
    row = item.metadata["evidence_passages"][0]
    assert row["content_role"] == "FORECAST_OR_MIXED_FINANCIAL_CONTEXT"
    assert row["context_labels"]["period_alignment"] == "NOT_RECONCILED"
    warning = extract(source(body='Quartz Tools warns customers to avoid phishing scams and has never requested passwords.'), domain="brand")
    assert warning.metadata["evidence_passages"][0]["content_role"] == "SAFETY_WARNING"
    correction = extract(source(body='Correction: Quartz Tools has recalled only one defective component, not all products.'), domain="brand")
    assert correction.metadata["evidence_passages"][0]["content_role"] == "CORRECTION_OR_RESPONSE"


def test_question_and_calendar_cannot_regain_prominence_as_extra_passages():
    item = extract(source(body='From live coverage: Will Quartz Tools smash earnings tonight?\n\n'
        'The company list includes Quartz Tools and others likely to issue earnings surprises.\n\n'
        'Quartz Tools reported revenue of USD 12 million and has published its financial results.'))
    assert len(item.metadata["evidence_passages"]) == 1
    assert "USD 12 million" in item.metadata["evidence_passages"][0]["text"]


@pytest.mark.parametrize("domain", ["financial", "trending", "brand", "personal"])
def test_read_diversity_breaks_ties_without_promoting_irrelevant_candidates(domain):
    first = EvidenceItem(id="a", canonical_url="https://first.example/a", title="Quartz Tools reported revenue earnings phishing interview announcement")
    second = EvidenceItem(id="b", canonical_url="https://second.example/b", title=first.title)
    counts = Counter({"first.example": 3})
    assert _read_priority(second, "Quartz Tools", domain, Counter(), counts) < _read_priority(first, "Quartz Tools", domain, Counter(), counts)
