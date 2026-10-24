"""Saved readable-text interpretation, not original-HTML or fresh-network proof."""
import copy
import hashlib
import json
from pathlib import Path

import pytest

from backend.infrastructure.acquisition.adapters.web.page_extraction import observe_anchored_article_body
from backend.services.research.body_context import reconcile_captured_context
from backend.services.research.passage_extractor import PassageExtractor, has_usable_passage
from backend.services.research.raw_pool import RawAcquisitionPool
from backend.services.research.research_models import EvidenceItem


FIXTURE = Path(__file__).parents[1] / "fixtures" / "acquisition" / "2026-10-22_wion_text_capture.json"


def capture():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def item_from_capture(saved):
    return EvidenceItem(id=saved["source_id"], canonical_url=saved["url"], title=saved["title"],
        content=saved["readable_text"], content_depth="FULL_TEXT", read_status="SUCCESS",
        metadata={"read_success": True, "page_metadata": copy.deepcopy(saved["page_metadata"]),
                  "acquired_at": saved["observed_at"]})


def test_genuine_text_capture_hash_and_exact_partial_body_spans():
    saved = capture()
    assert saved["fixture_origin"] == "GENUINE_SAVED_TEXT_CAPTURE_NOT_ORIGINAL_HTML"
    assert hashlib.sha256(saved["readable_text"].encode()).hexdigest() == saved["readable_text_sha256"]
    result = observe_anchored_article_body(saved["readable_text"], saved["page_metadata"])
    assert result and result["scope"] == "PARTIAL_ARTICLE_SPANS"
    assert len(result["spans"]) >= 3
    spans = [saved["readable_text"][row["start"]:row["end"]] for row in result["spans"]]
    assert any("The video impersonated Cook" in text for text in spans)
    assert all("Rafale Marine fighter" not in text and "What is the real meaning" not in text for text in spans)
    assert sum(len(text.split()) for text in spans) < 300
    assert result["publication_timestamp_inferred"] is False
    assert result["evidence_qualified"] is False


def test_reconciliation_keeps_full_source_hash_identity_and_unknown_publication():
    saved = capture()
    item = item_from_capture(saved)
    before = (item.id, item.canonical_url, item.content, item.published_at, item.metadata["acquired_at"])
    reconcile_captured_context(item)
    reconcile_captured_context(item)  # idempotent native/replay bridge
    assert (item.id, item.canonical_url, item.content, item.published_at, item.metadata["acquired_at"]) == before
    page = item.metadata["page_metadata"]
    assert page["content_scope"] == "body_fallback"
    assert page["body_kind"] == "ARTICLE_BODY"
    assert page["original_body_quality"]["body_kind"] == "UNCLASSIFIED_PAGE"
    assert page["body_quality"]["scope"] == "PARTIAL_ARTICLE_SPANS"
    pool = RawAcquisitionPool("saved-text-control")
    pool.add_capture(item)
    source = pool.export()["sources"][0]
    assert source["source_type"] == "ARTICLE_BODY"
    assert source["readable_text"] == saved["readable_text"]
    assert source["raw_content_hash"] == saved["readable_text_sha256"]


def test_personal_passage_is_exact_reported_incident_not_invented_cook_speech():
    saved = capture()
    item = item_from_capture(saved)
    reconcile_captured_context(item)
    PassageExtractor().extract_passages([item], "Tim Cook", domain="personal")
    assert has_usable_passage(item)
    assert "The video impersonated Cook" in item.relevant_excerpt
    assert item.content[item.excerpt_start:item.excerpt_end] == item.relevant_excerpt
    assert "Rafale" not in item.relevant_excerpt
    assert item.published_at == ""  # visible byline date remains unparsed, not today's incident


@pytest.mark.parametrize("change", ["no_byline", "no_heading", "wrong_title", "short_prose", "heading_only", "ambiguous_title", "bad_offsets"])
def test_structural_recovery_rejects_unanchored_or_menu_only_controls(change):
    saved = capture()
    text, page = saved["readable_text"], copy.deepcopy(saved["page_metadata"])
    if change == "no_byline":
        text = text.replace("Authored By Prajvi Mathur Published:", "Navigation and recommended reading:")
    elif change == "no_heading":
        page["text_blocks"] = []
    elif change == "wrong_title":
        page["title"] = "An unrelated publisher headline that was not observed here"
    elif change == "short_prose":
        # A title/byline and a single sentence are not an article body.
        text = text[:438] + "\n\nOne short observed sentence is not enough."
        page["text_blocks"] = [row for row in page["text_blocks"] if row["end"] <= 438]
    elif change == "heading_only":
        # News/card menus can contain the target and incident keywords.
        page["text_blocks"].extend({"start": match[0], "end": match[1], "role": "HEADING"}
            for match in [(440, 793), (795, 1009), (1011, 1330), (1450, 1703)])
        # A heading immediately after the byline is an explicit boundary.
        page["text_blocks"].append({"start": 440, "end": 500, "role": "HEADING"})
    elif change == "ambiguous_title":
        page["text_blocks"].append(dict(page["text_blocks"][0]))
    elif change == "bad_offsets":
        page["text_blocks"][0]["start"] = -1
    assert observe_anchored_article_body(text, page) is None


def test_mutated_capture_cannot_reuse_previous_recovery_spans():
    saved = capture()
    item = item_from_capture(saved)
    reconcile_captured_context(item)
    item.content += "\n\nTim Cook said unrelated words in a different altered capture."
    PassageExtractor().extract_passages([item], "Tim Cook", domain="personal")
    assert not item.relevant_excerpt


def test_metadata_only_response_cannot_gain_article_recovery():
    saved = capture()
    item = item_from_capture(saved)
    item.metadata["read_success"] = False
    reconcile_captured_context(item)
    assert "article_body_recovery" not in item.metadata["page_metadata"]


def test_short_related_heading_stops_recovery_before_card_prose():
    saved = capture()
    boundary = 1705  # Start of observed related-story headings, not a body cut.
    text = saved["readable_text"][:boundary] + "Related stories\n\n" + (
        "Tim Cook reported a fake crypto scam involving an unrelated platform. " * 3)
    page = copy.deepcopy(saved["page_metadata"])
    page["text_blocks"] = [row for row in page["text_blocks"] if row["end"] <= boundary]
    page["text_blocks"].append({"role": "HEADING", "start": boundary, "end": boundary + len("Related stories")})
    recovery = observe_anchored_article_body(text, page)
    assert recovery and recovery["selection_end"] == boundary
    assert all(row["end"] <= boundary for row in recovery["spans"])


def test_replaced_bytes_lose_old_structural_label_and_pool_article_count():
    saved = capture()
    item = item_from_capture(saved)
    reconcile_captured_context(item)
    item.content = "Only navigation and links remain in this replacement capture."
    reconcile_captured_context(item)
    page = item.metadata["page_metadata"]
    assert "article_body_recovery" not in page
    assert page["body_quality"]["body_kind"] == "UNCLASSIFIED_PAGE"
    assert page["body_kind"] == "UNCLASSIFIED_PAGE"
    pool = RawAcquisitionPool("replacement-control")
    pool.add_capture(item)
    assert pool.stats()["article_bodies"] == 0


def test_pool_preserves_scoped_recovery_and_original_quality_without_arbitrary_metadata():
    saved = capture()
    item = item_from_capture(saved)
    reconcile_captured_context(item)
    page = item.metadata["page_metadata"]
    page["article_body_recovery"]["cookie"] = "must-not-survive"
    page["original_body_quality"]["authorization"] = "must-not-survive"
    pool = RawAcquisitionPool("scope-serialization-control")
    pool.add_capture(item)
    exported = pool.export()
    stored = exported["sources"][0]["page_metadata"]
    assert stored["original_body_quality"]["link_text_ratio"] == 0.6114
    assert stored["body_quality"]["scope"] == "PARTIAL_ARTICLE_SPANS"
    assert stored["article_body_recovery"]["source_text_sha256"] == saved["readable_text_sha256"]
    assert "must-not-survive" not in json.dumps(exported)
    restored = RawAcquisitionPool.from_export(exported).to_evidence_items()[0]
    assert restored.metadata["page_metadata"]["article_body_recovery"]["spans"] == stored["article_body_recovery"]["spans"]
    assert restored.content == saved["readable_text"]
    assert restored.metadata["acquired_at"] == saved["observed_at"]


@pytest.mark.parametrize("change", ["replaced_bytes", "malformed_scope"])
def test_direct_pool_capture_cannot_count_invalid_recovery_as_article(change):
    item = item_from_capture(capture())
    reconcile_captured_context(item)
    if change == "replaced_bytes":
        item.content = "An unrelated replacement body without observed article structure."
    else:
        item.metadata["page_metadata"]["article_body_recovery"] = None
    pool = RawAcquisitionPool("invalid-recovery-control")
    pool.add_capture(item)  # Even without an intervening reconciliation call.
    assert pool.stats()["article_bodies"] == 0


def test_saved_text_reaches_real_harvest_pipeline_before_pool_classification():
    from datetime import datetime
    from scripts.audits.replay_specialist_completion import replay

    saved = capture()
    item = item_from_capture(saved)
    item.discovered_at = saved["observed_at"]
    pool = RawAcquisitionPool("genuine-text-only-replay")
    pool.add_capture(item)
    original = pool.export(include_text=True)
    assert original["sources"][0]["source_type"] == "DISCOVERY_LEAD"
    payload = {"research_corpus": {"raw_acquisition_pool": original,
        "deep_read_sources": [item.to_dict()], "raw_candidates": [item.to_dict()]}}
    # Only HarvestingEngine's acquired source set is substituted. Current
    # qualification, passage selection, specialist and API/SSE assembly run.
    result, _ = replay(payload, "personal_watch", "Tim Cook",
        reference_time=datetime.fromisoformat(saved["observed_at"]))
    current = result["research_corpus"]["raw_acquisition_pool"]["sources"][0]
    assert current["source_type"] == "ARTICLE_BODY"
    assert current["qualification_status"] == "QUALIFIED"
    assert current["source_id"] == saved["source_id"]
    assert current["raw_content_hash"] == saved["readable_text_sha256"]
    assert current["readable_text"] == saved["readable_text"]
    assert current["acquired_at"] == saved["observed_at"]
    assert current["published_at"] == original["sources"][0]["published_at"]
    assert len(result["evidence"]) == 1
    assert not result["public_statements"]  # reported impersonation is not Cook speaking
