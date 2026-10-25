"""Offline passage controls; token normalization is not evidence entailment."""
from types import SimpleNamespace

import pytest

from backend.services.research.entity_resolver import entity_resolver
from backend.services.research.passage_extractor import PassageExtractor
from backend.services.research.research_models import EvidenceItem


def extract(monkeypatch, target, body, *, kind="topic", temporal=True, depth="DEEP_READ"):
    monkeypatch.setattr(entity_resolver, "parse_request", lambda _: SimpleNamespace(
        target_entity=SimpleNamespace(entity_type=kind, aliases=[])))
    item = EvidenceItem(id="plural-case", canonical_url="https://publisher.example/article",
        title=target, content=body, content_depth=depth, acquired_id="observed-capture",
        metadata={"layer2_eligible": True, "temporal_required": True,
                  "temporal_eligible": temporal, "page_metadata": {"body_kind": "ARTICLE_BODY"}})
    PassageExtractor().extract_passages([item], target, domain="trending")
    return item


@pytest.mark.parametrize("target,body", [
    ("battery recycling", "Producer responsibility is intended to secure financing for the future collection and recycling of batteries and should be shared fairly among companies that place products on the market, the association said."),
    ("municipal policy", "Municipal policies were announced by the local authority after a public consultation. The source reports the new rules will apply to waste collection services from next month."),
    ("industry regulation", "The industry regulations were announced after consultation with local operators. The source reports that implementation is conditional on approval from the relevant authority."),
])
def test_regular_topic_plurals_preserve_exact_qualified_paragraph(monkeypatch, target, body):
    item = extract(monkeypatch, target, body)
    assert item.extraction_status == "SUCCESS"
    assert item.relevant_excerpt == body
    assert item.content[item.excerpt_start:item.excerpt_end] == body


@pytest.mark.parametrize("changes", [
    {"target": "battery manufacturing"}, {"temporal": False}, {"depth": "INDEX_SNIPPET"},
])
def test_plural_handling_does_not_bypass_topic_date_or_depth(monkeypatch, changes):
    options = {"target": "battery recycling", "body": "The association said the recycling of batteries is intended to finance future collection services. The proposal remains subject to approval by the government."}
    options.update(changes)
    item = extract(monkeypatch, **options)
    assert item.extraction_status != "SUCCESS"
    assert not item.metadata.get("evidence_passages")


def test_person_name_is_not_plural_normalized(monkeypatch):
    item = extract(monkeypatch, "Elena Banks", "Elena Bank announced a new battery recycling initiative. The source reports that the proposal still requires regulatory approval.", kind="person")
    assert item.extraction_status != "SUCCESS"


def test_actual_generic_request_classifier_reaches_plural_passage():
    body = "Producer responsibility is intended to secure financing for the future collection and recycling of batteries and should be shared fairly among companies that place products on the market, the association said."
    item = EvidenceItem(id="actual-request", canonical_url="https://publisher.example/article",
        title="Recycling requirements", content=body, content_depth="DEEP_READ", acquired_id="capture",
        metadata={"layer2_eligible": True, "temporal_required": True, "temporal_eligible": True,
                  "page_metadata": {"body_kind": "ARTICLE_BODY"}})
    PassageExtractor().extract_passages([item], "battery recycling", domain="trending")
    assert item.extraction_status == "SUCCESS" and item.relevant_excerpt == body
