"""Exact recovered-body scope controls; saved-text replay, not live proof."""
import copy
import json
from pathlib import Path

import pytest

from backend.agents.brandshield.intelligence import classify_brand_source
from backend.services.research.body_context import reconcile_captured_context
from backend.services.research.passage_records import captured_passages, public_statement_attribution
from backend.services.research.research_models import EvidenceItem


FIXTURE = Path(__file__).parents[1] / "fixtures" / "acquisition" / "2026-10-22_wion_text_capture.json"


def recovered_record(tail="", metadata_key="metadata"):
    saved = json.loads(FIXTURE.read_text(encoding="utf-8"))
    item = EvidenceItem(id=saved["source_id"], canonical_url=saved["url"], title=saved["title"],
        content=saved["readable_text"] + tail, content_depth="FULL_TEXT", read_status="SUCCESS",
        metadata={"read_success": True, "page_metadata": copy.deepcopy(saved["page_metadata"]),
                  "acquired_at": saved["observed_at"]})
    reconcile_captured_context(item)
    assert item.metadata["page_metadata"]["article_body_recovery"]
    return {"evidence_id": item.id, "canonical_url": item.canonical_url, "url": item.canonical_url,
        "title": item.title, "content": item.content, "content_depth": item.content_depth,
        metadata_key: copy.deepcopy(item.metadata)}


@pytest.mark.parametrize("metadata_key", ["metadata", "raw_metadata"])
def test_related_incident_card_cannot_regain_brand_classification_or_passage(metadata_key):
    card = ("Contoso reported that investigators uncovered a counterfeit operation where its products were sold "
            "by an unauthorized online store. This synthetic related card is outside the acquired article scope.")
    record = recovered_record("\n\n" + card, metadata_key=metadata_key)
    before = copy.deepcopy(record)
    rows = captured_passages(record, domain="brand", target="Contoso")
    assert not any(card == row["text"] for row in rows)
    result = classify_brand_source(record, "Contoso")
    assert result["classification"] == "INSUFFICIENT_EVIDENCE"
    assert result["actor_url"] is None
    assert record == before


@pytest.mark.parametrize("metadata_key", ["metadata", "raw_metadata"])
def test_outside_quotation_cannot_become_public_statement(metadata_key):
    quote = 'Tim Cook said, "This unrelated card contains a synthetic attributed quotation for the scope control."'
    record = recovered_record("\n\n" + quote, metadata_key=metadata_key)
    assert public_statement_attribution(record, quote, "Tim Cook") is None
    rows = captured_passages(record, domain="personal", target="Tim Cook")
    assert not any(quote == row["text"] for row in rows)
    assert not any(row["content_role"] == "PUBLIC_STATEMENT" for row in rows)
    incident = [row for row in rows if "The video impersonated Cook" in row["text"]]
    assert incident and incident[0]["content_role"] == "UNVERIFIED_ALLEGATION"
    assert all(record["content"][row["start"]:row["end"]] == row["text"] for row in rows)


@pytest.mark.parametrize("corruption", ["hash", "basis", "spans", "null"])
def test_invalid_recovered_scope_cannot_fall_back_to_whole_body(corruption):
    record = recovered_record()
    recovery = record["metadata"]["page_metadata"]["article_body_recovery"]
    if corruption == "hash":
        recovery["source_text_sha256"] = "0" * 64
    elif corruption == "basis":
        recovery["basis"] = "INFERRED"
    elif corruption == "spans":
        recovery["spans"] = [{"start": -1, "end": len(record["content"])}]
    else:
        record["metadata"]["page_metadata"]["article_body_recovery"] = None
    before = copy.deepcopy(record)
    assert captured_passages(record, domain="personal", target="Tim Cook") == []
    result = classify_brand_source(record, "Apple")
    assert result["classification"] == "INSUFFICIENT_EVIDENCE"
    assert result["reason"] == "NO_VALID_RECOVERED_ARTICLE_SPANS"
    assert record == before


def test_valid_recovered_incident_remains_source_report_not_observed_actor():
    record = recovered_record()
    before = copy.deepcopy(record)
    result = classify_brand_source(record, "Apple")
    assert result["classification"] == "REPORTED_ALLEGATION"
    assert result["actor_url"] is None
    assert result["epistemic_state"] == "UNVERIFIED"
    assert record == before


@pytest.mark.parametrize("invalid", [False, True])
def test_public_serializer_preserves_safe_scope_and_fail_closed_marker(invalid):
    from backend.schemas.evidence_inspection import public_capture_metadata
    record = recovered_record()
    page = record["metadata"]["page_metadata"]
    page["article_body_recovery"]["headers"] = {"Cookie": "do-not-export"}
    if invalid:
        page["article_body_recovery"]["source_text_sha256"] = "0" * 64
    result = public_capture_metadata(record)
    recovery = result["page_metadata"]["article_body_recovery"]
    assert "headers" not in recovery
    assert recovery["evidence_qualified"] is False
    if invalid:
        assert recovery["basis"] == "INVALID_CAPTURED_ARTICLE_RECOVERY"
    else:
        assert recovery["source_text_sha256"] == page["article_body_recovery"]["source_text_sha256"]
        assert recovery["spans"] == page["article_body_recovery"]["spans"]
        assert result["page_metadata"]["original_body_quality"]["body_kind"] == "UNCLASSIFIED_PAGE"


def test_personal_native_normalizer_keeps_article_boundary_and_no_fake_speech():
    from backend.agents.personal_watch.monitoring import normalize_item
    from backend.agents.personal_watch.assessment import synthesize_personal_threats
    quote = 'Tim Cook said, "An outside synthetic card must not be attributed as a genuine public statement."'
    record = recovered_record("\n\n" + quote)
    before = copy.deepcopy(record)
    native = normalize_item(record, "Web", "SECONDARY_REPORTING", "Tim Cook")
    assert native["evidence_id"] == record["evidence_id"]
    assert native["content"] == record["content"]
    assert native["metadata"]["page_metadata"]["article_body_recovery"]["spans"]
    native_before = copy.deepcopy(native)
    result = synthesize_personal_threats({"name": "Tim Cook", "canonical_name": "Tim Cook"}, [native])
    assert not result["public_statements"]
    assert all(quote not in passage["text"] for passage in captured_passages(native, "personal", "Tim Cook"))
    assert native == native_before
    assert result["identity_authenticated"] is False
    assert record == before


def test_brand_native_scanner_keeps_article_boundary(monkeypatch):
    from types import SimpleNamespace
    from backend.agents.brandshield.scanning import search_brand_evidence
    from backend.services.research import research_engine
    record = recovered_record("\n\nContoso reported a counterfeit operation seized by police. This unrelated incident card must stay outside the article scope.")
    item = EvidenceItem(id=record["evidence_id"], canonical_url=record["url"], title=record["title"],
        content=record["content"], content_depth="FULL_TEXT", read_status="SUCCESS",
        metadata=copy.deepcopy(record["metadata"]))
    monkeypatch.setattr(research_engine, "investigate", lambda request: SimpleNamespace(evidence=[item], telemetry={}))
    sources, _, _, _, _ = search_brand_evidence({"brand": "Apple"})
    assert len(sources) == 1
    source = sources[0]
    assert source["evidence_id"] == item.id
    assert source["content"] == item.content
    assert source["raw_metadata"]["page_metadata"]["article_body_recovery"]["spans"]
    assert classify_brand_source(source, "Contoso")["classification"] == "INSUFFICIENT_EVIDENCE"
    assert not any("Contoso" in row["text"] for row in captured_passages(source, "brand", "Contoso"))


def test_legacy_selected_span_cannot_restore_outside_related_card():
    from backend.agents.brandshield.assessment import synthesize_brand_threats
    card = ("Contoso reported that investigators uncovered a counterfeit operation where its products were sold "
            "by an unauthorized online store. This synthetic related card is outside the acquired article scope.")
    source = recovered_record("\n\n" + card, metadata_key="raw_metadata")
    source["platform"] = "Web"
    offset = source["content"].index(card)
    source["selected_research_excerpt"] = {"text": card, "start": offset, "end": offset + len(card), "qualified": True}
    original_content = source["content"]
    result = synthesize_brand_threats({"brand": "Contoso"}, [source])
    assert not any(card == row["text"] for row in source["passages"])
    assert not result["threats"]
    assert source["content"] == original_content
