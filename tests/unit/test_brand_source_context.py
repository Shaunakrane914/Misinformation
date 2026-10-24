"""Synthetic source-role calibration, not live or independent accuracy proof."""
import copy

import pytest

from backend.agents.brandshield.assessment import synthesize_brand_threats
from backend.agents.brandshield.intelligence import classify_brand_source


def record(body, **changes):
    return {"evidence_id": "brand-source", "title": "Cedar public report", "content": body,
            "snippet": body, "url": "https://publisher.example/security-report", "platform": "Web",
            "content_depth": "PARTIAL_CONTENT", **changes}


@pytest.mark.parametrize("body,classification,actor", [
    ("Cedar replicas for sale. Buy now and add to cart.", "REPORTED_ALLEGATION", False),
    ("Replica Cedar shoes for sale. Add to cart.", "OBSERVED_SUSPICIOUS_ACTIVITY", True),
    ("Researchers reported that a fake Cedar page instructed users to enter passwords.", "REPORTED_ALLEGATION", False),
    ("Cedar customer complaint: I ordered shoes and never received my order. This feels like a scam.", "CUSTOMER_COMPLAINT", False),
    ("Customs officers seized counterfeit Cedar shoes. The report describes a prior enforcement operation.", "HISTORICAL_ENFORCEMENT", False),
    ("Cedar warns: beware of phishing messages and protect yourself from scams.", "WARNING_ADVISORY", False),
    ("Cedar introduced shoes in new colours. The collection is available at retailers.", "BACKGROUND_INFORMATION", False),
])
def test_source_context_categories_do_not_conflate_reporting_and_observation(body, classification, actor):
    outcome = classify_brand_source(record(body), "Cedar")
    # A non-imperative product sentence is conservatively a report even if it
    # mentions sales. It cannot authenticate a publisher as the seller.
    assert outcome["classification"] == classification
    assert bool(outcome["actor_url"]) is actor
    assert outcome["ownership_verified"] is False


def test_reporting_publisher_never_becomes_actor_or_takedown_target():
    source = record("Researchers reported a fake Cedar giveaway that instructed users to enter passwords. The incident allegation is unverified.")
    before = copy.deepcopy(source)
    result = synthesize_brand_threats({"brand": "Cedar"}, [source])
    assert result["threats"]
    assert all(threat["classification"] == "REPORTED_ALLEGATION" and not threat["is_threat"] for threat in result["threats"])
    assert not result["counterfeits"] and not result["impersonations"]
    assert all(threat["actor_url"] is None and threat["confidence"] is None for threat in result["threats"])
    assert all(dossier["actor_url"] is None and "does not justify" in dossier["recommended_action"] for dossier in result["dossiers"])
    assert source["content"] == before["content"]
    assert all(source["content"][p["start"]:p["end"]] == p["text"] for p in source["passages"])


def test_official_warning_retained_separately_without_creating_active_threat():
    source = record("Cedar warns customers to avoid phishing scams. We never request account passwords through email.", source_role="PRIMARY")
    result = synthesize_brand_threats({"brand": "Cedar"}, [source])
    assert result["source_assessments"][0]["classification"] == "OFFICIAL_WARNING"
    assert result["advisories"][0]["is_threat"] is False
    assert result["advisories"][0]["actor_url"] is None
    assert not any(threat.get("is_threat") for threat in result["threats"])


def test_navigation_title_and_explicit_snippet_cannot_establish_incident():
    source = record("Title: Cedar counterfeit operation seized\n\nMarkdown Content:\n\n[Press releases](https://agency.example/news)")
    assert classify_brand_source(source, "Cedar")["classification"] == "INSUFFICIENT_EVIDENCE"
    source = record("Cedar scam reportedly stole credentials.", content_depth="SNIPPET")
    assert classify_brand_source(source, "Cedar")["classification"] == "INSUFFICIENT_EVIDENCE"


def test_unrelated_warning_is_not_brand_warning():
    source = record("Birch warns customers about phishing messages.", title="Birch warning")
    assert classify_brand_source(source, "Cedar")["classification"] == "INSUFFICIENT_EVIDENCE"


def test_adjacent_incident_paragraphs_preserve_exact_article_span_without_title_as_body():
    from backend.services.research.research_models import EvidenceItem
    from backend.services.research.passage_extractor import passage_extractor, has_usable_passage
    anchor = "Investigators unearthed an illicit operation distributing Cedar footwear dupes through a commercial warehouse."
    continuation = "The warehouse was inspected and counterfeit products were seized under a search warrant; no arrest was reported."
    body = "A publisher navigation heading\n\n" + anchor + "\n\n" + continuation
    item = EvidenceItem(id="adjacent-incident", title="Cedar counterfeit operation", content=body,
                        content_depth="PARTIAL_CONTENT", canonical_url="https://publisher.example/incident",
                        metadata={"read_success": True, "page_metadata": {"body_kind": "ARTICLE_BODY"}})
    passage_extractor.extract_passages([item], "Cedar", domain="brand")
    assert item.relevant_excerpt == anchor + "\n\n" + continuation
    assert body[item.excerpt_start:item.excerpt_end] == item.relevant_excerpt
    assert has_usable_passage(item)
    assert item.metadata["excerpt_context"] == "BOUNDED_ADJACENT_ARTICLE_PARAGRAPHS"


@pytest.mark.parametrize("separator,acquired", [("\n\nRelated Stories\n\n", True), ("\n\n", False)])
def test_incident_context_cannot_cross_sidebar_or_borrow_unacquired_text(separator, acquired):
    from backend.services.research.research_models import EvidenceItem
    from backend.services.research.passage_extractor import passage_extractor
    body = ("Investigators unearthed an illicit operation distributing Cedar footwear dupes through a commercial warehouse."
            + separator + "The warehouse was inspected and counterfeit products were seized under a search warrant.")
    item = EvidenceItem(id="not-borrowed", content=body, title="Cedar counterfeit report", content_depth="PARTIAL_CONTENT",
                        canonical_url="https://publisher.example/incident",
                        metadata={"read_success": acquired, "page_metadata": {"body_kind": "ARTICLE_BODY"}})
    passage_extractor.extract_passages([item], "Cedar", domain="brand")
    assert item.extraction_status == "NO_RELEVANT_PASSAGE"


def test_validated_shared_excerpt_survives_brand_projection_with_native_offsets():
    anchor = "Investigators unearthed an illicit operation distributing Cedar footwear dupes through a commercial warehouse."
    following = "The warehouse was inspected and counterfeit products were seized under a search warrant."
    excerpt = anchor + "\n\n" + following
    source = record(excerpt, selected_research_excerpt={"text": excerpt, "start": 0, "end": len(excerpt), "qualified": True})
    result = synthesize_brand_threats({"brand": "Cedar"}, [source])
    assert result["threats"]
    for threat in result["threats"]:
        assert threat["classification"] == "HISTORICAL_ENFORCEMENT"
        assert threat["actor_url"] is None and threat["is_threat"] is False
        spans = [p for p in threat["supporting_passages"] if p.get("selection_method") == "VALIDATED_SHARED_RESEARCH_SPAN"]
        assert spans and source["content"][spans[0]["start"]:spans[0]["end"]] == excerpt


def test_short_selected_span_cannot_erase_acquired_enforcement_context():
    anchor = "Investigators reported Cedar counterfeit goods being distributed from an illicit warehouse operation."
    next_paragraph = "The merchandise carried copied branding and was offered to buyers as genuine footwear."
    excerpt = anchor + "\n\n" + next_paragraph
    body = excerpt + "\n\nOfficers executed a search warrant and seized the goods; no arrests were reported."
    source = record(body, selected_research_excerpt={"text": excerpt, "start": 0, "end": len(excerpt), "qualified": True})
    result = synthesize_brand_threats({"brand": "Cedar"}, [source])
    assert result["threats"]
    assert result["source_assessments"][0]["classification"] == "HISTORICAL_ENFORCEMENT"
    assert all(threat["classification"] == "HISTORICAL_ENFORCEMENT" and not threat["is_threat"]
               and threat["actor_url"] is None for threat in result["threats"])
