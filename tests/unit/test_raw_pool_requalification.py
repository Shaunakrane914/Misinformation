"""Deterministic saved-source requalification, never live research evidence."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest

from backend.services.research.raw_pool import RawAcquisitionPool
from backend.services.research.research_models import EvidenceItem
from scripts.audits.requalify_raw_pool import locate_pool, requalify_payload


REPO_ROOT = Path(__file__).resolve().parents[2]
CLI = REPO_ROOT / "scripts" / "audits" / "requalify_raw_pool.py"


def pool_fixture():
    pool = RawAcquisitionPool("offline-control")
    source = EvidenceItem(id="original-native-id", canonical_url="https://publisher.example/reports/cedar-results",
        title="Cedar Instruments reported quarterly results", source_name="Observed Publisher",
        content="Cedar Instruments reported revenue of USD 14 million for the quarter. The reported number was not independently audited.\n\n"
                "The company announced a revised financial forecast after reviewing the reported results with its board.",
        content_depth="PARTIAL_CONTENT", published_at="2026-10-20T04:00:00+00:00",
        metadata={"read_success": True, "page_metadata": {"body_quality": {"body_kind": "ARTICLE_BODY"}}})
    pool.add_capture(source)
    pool.mark_qualification(source.id, "QUALIFIED", useful_words=5)
    pool.add_candidate(EvidenceItem(id="lead-only", canonical_url="https://other.example/cedar", snippet="Unacquired snippet"))
    return pool.export()


@pytest.mark.parametrize("location", ["standalone", "research_corpus", "deep_research_trace", "top", "result"])
def test_documented_full_text_envelopes_requalify_without_modifying_original(location):
    raw = pool_fixture()
    if location == "standalone":
        payload = raw
    elif location == "top":
        payload = {"raw_acquisition_pool": raw}
    elif location == "result":
        payload = {"data": {"result": {"research_corpus": {"raw_acquisition_pool": raw}}}}
    else:
        payload = {location: {"raw_acquisition_pool": raw}}
    before = copy.deepcopy(payload)
    result = requalify_payload(payload, target="Cedar Instruments", domain="financial")
    assert payload == before
    assert result["mode"] == "OFFLINE_RAW_REQUALIFICATION"
    assert result["fresh_network_calls"] == 0 and result["model_calls"] == 0
    assert result["new_source_acquisition"] is False
    assert result["raw_acquisition_pool"] == raw
    assert result["requalification"]["stats"]["qualified_source_count"] == 1
    qualified = result["requalification"]["decisions"][0]
    assert qualified["source_id"] == "original-native-id"
    passage = qualified["passage"]
    original_text = raw["sources"][0]["readable_text"]
    assert original_text[passage["start"]:passage["end"]] == passage["text"]
    assert "not independently audited" in passage["text"]
    assert passage["claim_support"] == "NOT_ADJUDICATED"
    assert result["requalification"]["decisions"][1]["reasons"] == ["NO_ACQUIRED_SOURCE_TEXT"]


def test_textless_projection_rejected_but_full_pool_preferred_when_both_present():
    raw = pool_fixture()
    textless = copy.deepcopy(raw)
    for source in textless["sources"]:
        source.pop("readable_text")
    with pytest.raises(ValueError, match="TEXTLESS_POOL_NOT_REPROCESSABLE"):
        locate_pool({"deep_research_trace": {"raw_acquisition_pool": textless}})
    assert locate_pool({"research_corpus": {"raw_acquisition_pool": raw},
        "deep_research_trace": {"raw_acquisition_pool": textless}}) == raw


def test_unknown_long_capture_and_wrong_subject_cannot_be_qualified():
    raw = pool_fixture()
    raw["sources"][0]["source_type"] = "DISCOVERY_LEAD"
    raw["sources"][0]["page_metadata"]["body_quality"]["body_kind"] = "UNCLASSIFIED_PAGE"
    result = requalify_payload(raw, target="Cedar Instruments", domain="financial")
    assert result["requalification"]["stats"]["qualified_source_count"] == 0
    assert result["requalification"]["decisions"][0]["reasons"] == ["NO_ELIGIBLE_STRUCTURAL_BODY"]
    raw["sources"][0]["source_type"] = "ARTICLE_BODY"
    result = requalify_payload(raw, target="Cedar Instruments", domain="financial")
    assert result["requalification"]["stats"]["qualified_source_count"] == 0
    assert result["requalification"]["decisions"][0]["reasons"] == ["NO_ELIGIBLE_STRUCTURAL_BODY"]
    result = requalify_payload(pool_fixture(), target="Willow Medical", domain="financial")
    assert result["requalification"]["stats"]["qualified_source_count"] == 0
    assert result["requalification"]["decisions"][0]["passage"] is None


def test_exact_duplicate_stays_inspectable_without_double_qualification():
    raw = pool_fixture()
    duplicate = copy.deepcopy(raw["sources"][0])
    duplicate["source_id"] = "duplicate-native-id"
    duplicate["source_url"] = "https://second.example/reprint"
    duplicate["canonical_url"] = duplicate["source_url"]
    duplicate["source_urls"] = [duplicate["source_url"]]
    duplicate["publisher_host"] = "second.example"
    raw["sources"].append(duplicate)
    result = requalify_payload(raw, target="Cedar Instruments", domain="financial")
    assert result["requalification"]["stats"]["qualified_source_count"] == 1
    assert result["requalification"]["stats"]["duplicate_captures"] == 1
    assert result["requalification"]["decisions"][2]["qualification_status"] == "DUPLICATE"
    assert result["raw_acquisition_pool"]["sources"][2]["readable_text"] == duplicate["readable_text"]


def test_missing_trending_date_is_not_replaced_by_saved_acquisition_time():
    from datetime import datetime, timezone
    raw = pool_fixture()
    source = raw["sources"][0]
    source["published_at"] = None
    result = requalify_payload(raw, target="Cedar Instruments", domain="trending",
        reference_time=datetime(2026, 10, 20, 12, tzinfo=timezone.utc))
    assert result["requalification"]["stats"]["qualified_source_count"] == 0
    assert result["requalification"]["decisions"][0]["observed_published_at"] is None


def test_cli_creates_only_new_report_and_preserves_saved_input(tmp_path):
    source = tmp_path / "captured.json"
    source.write_text(json.dumps({"research_corpus": {"raw_acquisition_pool": pool_fixture()}}), encoding="utf-8")
    original_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    output = tmp_path / "new" / "decision.json"
    command = [sys.executable, str(CLI), "--input", str(source), "--output", str(output),
        "--target", "Cedar Instruments", "--domain", "financial"]
    completed = subprocess.run(command, cwd=REPO_ROOT, capture_output=True, text=True, timeout=30)
    assert completed.returncode == 0, completed.stderr
    result = json.loads(output.read_text(encoding="utf-8"))
    assert result["mode"] == "OFFLINE_RAW_REQUALIFICATION"
    assert result["model_calls"] == 0 and result["input_sha256"] == original_hash
    assert result["network_policy"] == "LIVE_NETWORK_BLOCKED_BEFORE_APPLICATION_IMPORTS"
    assert result["requalification"]["stats"]["qualified_source_count"] == 1
    original_output = output.read_bytes()
    duplicate = subprocess.run(command, cwd=REPO_ROOT, capture_output=True, text=True, timeout=30)
    assert duplicate.returncode == 1 and "FileExistsError" in duplicate.stderr
    assert output.read_bytes() == original_output
    assert hashlib.sha256(source.read_bytes()).hexdigest() == original_hash


def test_cli_rejects_trace_without_text_and_naive_time_without_creating_output(tmp_path):
    raw = pool_fixture()
    for record in raw["sources"]:
        record.pop("readable_text")
    source, output = tmp_path / "textless.json", tmp_path / "must-not-exist.json"
    source.write_text(json.dumps({"deep_research_trace": {"raw_acquisition_pool": raw}}), encoding="utf-8")
    command = [sys.executable, str(CLI), "--input", str(source), "--output", str(output),
        "--target", "Cedar Instruments", "--domain", "financial"]
    completed = subprocess.run(command, cwd=REPO_ROOT, capture_output=True, text=True, timeout=30)
    assert completed.returncode == 1 and "TEXTLESS_POOL_NOT_REPROCESSABLE" in completed.stderr
    assert not output.exists()
    completed = subprocess.run(command + ["--reference-time", "2026-10-20T12:00:00"],
        cwd=REPO_ROOT, capture_output=True, text=True, timeout=30)
    assert completed.returncode == 1 and "timezone" in completed.stderr
    assert not output.exists()


def test_alias_disambiguation_requires_explicit_optin_and_preserves_original_capture(tmp_path):
    raw = pool_fixture()
    raw["sources"][1]["aliases"] = ["original-native-id"]
    original = copy.deepcopy(raw)
    with pytest.raises(ValueError, match="Conflicting source alias"):
        requalify_payload(raw, target="Cedar Instruments", domain="financial")
    result = requalify_payload(raw, target="Cedar Instruments", domain="financial", disambiguate_aliases=True)
    assert raw == original and result["raw_acquisition_pool"] == original
    assert result["alias_disambiguation"]["enabled"] is True
    assert result["alias_disambiguation"]["prior_citations_repaired"] is False
    assert result["alias_disambiguation"]["ambiguous_aliases"] == [{"alias": "original-native-id",
        "source_ids": ["lead-only", "original-native-id"], "excluded_from_alias_lookup": True}]
    assert result["requalification"]["decisions"][0]["source_id"] == "original-native-id"
    assert result["requalification"]["decisions"][0]["raw_content_hash"] == original["sources"][0]["raw_content_hash"]
    assert result["requalification"]["stats"]["qualified_source_count"] == 1
    source, output = tmp_path / "ambiguous.json", tmp_path / "rescue.json"
    source.write_text(json.dumps(raw), encoding="utf-8")
    command = [sys.executable, str(CLI), "--input", str(source), "--output", str(output),
        "--target", "Cedar Instruments", "--domain", "financial"]
    strict = subprocess.run(command, cwd=REPO_ROOT, capture_output=True, text=True, timeout=30)
    assert strict.returncode == 1 and not output.exists()
    explicit = subprocess.run(command + ["--disambiguate-aliases"], cwd=REPO_ROOT, capture_output=True, text=True, timeout=30)
    assert explicit.returncode == 0, explicit.stderr
    saved = json.loads(output.read_text(encoding="utf-8"))
    assert saved["alias_disambiguation"]["prior_citations_repaired"] is False
    assert saved["raw_acquisition_pool"] == raw
    assert json.loads(source.read_text(encoding="utf-8")) == original
