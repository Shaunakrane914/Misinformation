"""Offline specialist presentation controls, not new acquisition/accuracy proof."""
from copy import deepcopy

import pytest

from backend.agents.brandshield.intelligence import contextualize_brand_threat
from backend.services.research.specialist_brief import specialist_brief


def test_brand_coverage_brief_does_not_leak_identity_forensics_template():
    coverage, summary, steps = specialist_brief({}, "brandshield", "Example Brand", 3)
    assert coverage["status"] == "INSUFFICIENT_EVIDENCE"
    assert "profile" not in summary.lower() and "media forensics" not in summary.lower()
    assert "brand/source coverage" in summary
    assert "independently verified threat assessment" in summary
    assert "product-safety concerns" in summary
    assert not any("generic profiles" in step for step in steps)


def test_personal_coverage_brief_retains_relevant_identity_limitations():
    coverage, summary, steps = specialist_brief({}, "personal_watch", "Example Person", 3)
    assert coverage["status"] == "INSUFFICIENT_EVIDENCE"
    assert "including 0 profile(s)" in summary and "No media forensics" in summary
    assert "identity-abuse or synthetic-media exposure" in summary
    assert any("generic profiles" in step for step in steps)


@pytest.mark.parametrize("target,paragraph", [
    ("Cedar", "Cedar recalled some appliances because of a component issue. The publisher corrected an earlier headline that overstated the extent of the recall."),
    ("Birch", "The publisher reports a safety hazard involving Birch batteries, but the company disputes the allegations and no independent inspection was performed."),
])
def test_actual_product_safety_reporting_is_not_described_as_observed_scam(target, paragraph):
    source = {"evidence_id": "report", "url": "https://publisher.example/report", "title": target + " safety report",
              "content": paragraph, "content_depth": "PARTIAL_CONTENT"}
    before = deepcopy(source)
    threat = {"threat_type": "PRODUCT_SAFETY", "supporting_passages": [
        {"text": paragraph, "start": 0, "end": len(paragraph)}]}
    result = contextualize_brand_threat(threat, [source], target)
    assert result is not None and result["is_threat"] is False and result["actor_url"] is None
    assert result["epistemic_state"] == "UNVERIFIED" and result["confidence"] is None
    assert "product-safety issue or recall" in result["summary"]
    assert "suspicious incident" not in result["summary"]
    assert "does not establish counterfeit sales, phishing or fraud" in result["summary"]
    assert source == before and result["supporting_passages"][0]["text"] == paragraph


def test_legacy_product_label_without_acquired_recall_text_cannot_create_safety_report():
    source = {"evidence_id": "report", "url": "https://publisher.example/report", "title": "Cedar source report",
        "content": "Researchers reported that a fake Cedar page asked users to enter their account passwords.",
        "content_depth": "PARTIAL_CONTENT"}
    result = contextualize_brand_threat({"threat_type": "PRODUCT_SAFETY"}, [source], "Cedar")
    assert result["classification"] == "REPORTED_ALLEGATION" and result["is_threat"] is False
    assert "product-safety issue or recall" not in result["summary"]


def test_saved_native_dyson_recall_correction_text_is_preserved_exactly():
    # Genuine Oct23 native capture excerpt; no new source request or truth label.
    paragraph = ('Update 15:50 GMT: The article has been updated with the company\'s response. '
        'The headline was amended because the previous one might have given the impression that Dyson has pulled '
        'the product off the market, when in fact it has recalled only some toothbrushes because of "a component issue."')
    source = {"evidence_id": "ev_hv_6365e5f7eeccd30f09ae", "url": "https://cybernews.com/tech/dyson-ai-camerajet-toothbrush-suspended-sales/",
        "title": "Dyson CameraJet toothbrush users report significant issues", "content": paragraph,
        "content_depth": "PARTIAL_CONTENT"}
    passages = [{"text": paragraph, "start": 0, "end": len(paragraph)}]
    result = contextualize_brand_threat({"threat_type": "PRODUCT_SAFETY", "supporting_passages": deepcopy(passages)}, [source], "Dyson")
    assert result["is_threat"] is False and result["actor_url"] is None
    assert result["supporting_passages"] == passages
    assert 'recalled only some toothbrushes' in result["supporting_passages"][0]["text"]
    assert "company response" in result["summary"]
