"""Genuine saved prefixes and synthetic controls, not live discovery/accuracy."""
import json
from pathlib import Path

import pytest

from backend.services.research.passage_extractor import PassageExtractor, has_usable_passage
from backend.services.research.research_models import EvidenceItem
from backend.services.research.trend_context import classify_source_context


CAPTURE = json.loads((Path(__file__).parent / "fixtures/oct21_trending_captured_prefixes.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("record", CAPTURE["records"][:2], ids=["observed-google-lead", "observed-aws-lead"])
def test_genuine_simple_past_announcement_beats_keyword_rich_history(record):
    body = "\n\n".join(record["paragraphs"])
    item = EvidenceItem(id=record["id"], canonical_url=record["url"], title=record["title"],
        content=body, content_depth="PARTIAL_CONTENT", metadata={"read_success": True})
    PassageExtractor().extract_passages([item], record["target"], domain="trending")
    assert item.relevant_excerpt == record["paragraphs"][0]
    assert item.content[item.excerpt_start:item.excerpt_end] == item.relevant_excerpt
    assert item.content == body
    assert item.id == record["id"]
    assert item.metadata["trend_source_context"]["classification"] == "COMPETITIVE_CONTEXT"


def test_genuine_former_affiliation_is_not_current_company_development():
    record = CAPTURE["records"][2]
    item = EvidenceItem(id=record["id"], canonical_url=record["url"], title=record["title"],
        content="\n\n".join(record["paragraphs"]), content_depth="PARTIAL_CONTENT")
    PassageExtractor().extract_passages([item], record["target"], domain="trending")
    assert not has_usable_passage(item)
    assert item.relevant_excerpt == ""
    assert item.metadata["post_read_qualification_reason"] == "FORMER_AFFILIATION_NOT_TARGET_EVENT"
    assert record["paragraphs"][1] in item.content


@pytest.mark.parametrize("target", ["Aster", "Boreal Labs", "Cedar"])
def test_heldout_name_competitive_context_is_labeled_not_primary(target):
    result = classify_source_context(f"Rival pressures {target} with new toolkit",
        f"On Monday, Rival released a toolkit to challenge {target}. No performance results have been verified.", target)
    assert result["classification"] == "COMPETITIVE_CONTEXT"


def test_former_employee_allegation_about_target_remains_investigable():
    result = classify_source_context("Former Aster employee alleges Aster concealed a breach",
        "A former employee alleges Aster concealed a breach. The allegation has not been independently verified.", "Aster")
    assert result["classification"] != "INCIDENTAL_MENTION"


def test_primary_target_report_not_demoted_just_for_competition_vocabulary():
    result = classify_source_context("Aster faces pressure over delayed filings",
        "Aster faces mounting pressure to publish its delayed filings. A rival announced a product last week.", "Aster")
    assert result["classification"] == "PRIMARY_TOPIC"


def test_negated_announcement_qualification_is_not_removed():
    lead = "On Tuesday, Aster announced that it had not released the proposed product. Testing may not begin until approval."
    history = "Historically, Aster had reported $40 million in 2016 and 80% revenue growth since 2012."
    item = EvidenceItem(id="generic", canonical_url="https://example.org/article", title="Aster testing update",
        content=lead + "\n\n" + history, content_depth="PARTIAL_CONTENT")
    PassageExtractor().extract_passages([item], "Aster", domain="trending")
    assert item.relevant_excerpt == lead
    assert "not released" in item.relevant_excerpt
    assert item.content[item.excerpt_start:item.excerpt_end] == lead


def test_shared_findings_prioritize_direct_reporting_over_competitive_context():
    from backend.application.research.synthesis import synthesize_grounded_findings
    items = []
    for index, (title, body) in enumerate([
        ("Rival challenges Aster", "Rival released a toolkit to challenge Aster on Tuesday. Independent performance results have not been verified and no market impact has been established."),
        ("Aster deployment", "Aster announced a deployment on Tuesday. Independent testing has not been completed."),
    ]):
        item = EvidenceItem(id=str(index), canonical_url=f"https://example.org/{index}", title=title,
            content=body, content_depth="PARTIAL_CONTENT", metadata={"read_success": True})
        PassageExtractor().extract_passages([item], "Aster", domain="trending")
        items.append(item)
    findings = synthesize_grounded_findings("Aster", "trending", items, [])
    assert findings[0].supporting_evidence_ids == ["1"]
    assert findings[1].supporting_evidence_ids == ["0"]
    assert findings[1].importance == "LOW"
    assert findings[1].metadata["source_context"]["classification"] == "COMPETITIVE_CONTEXT"
