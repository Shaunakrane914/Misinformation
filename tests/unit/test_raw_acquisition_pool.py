"""Offline raw-pool controls; synthetic bodies do not establish live retrieval."""
import hashlib
import json
from pathlib import Path

import pytest

from backend.services.research.raw_pool import RawAcquisitionPool, RawSourceType
from backend.services.research.research_models import EvidenceItem


def captured(source_id="source", url="https://publisher.example/reports/2026/results", **kwargs):
    return EvidenceItem(id=source_id, canonical_url=url,
        title="Cedar Instruments quarterly results", source_name="Observed Publisher",
        content="Cedar Instruments reported revenue of USD 14 million. The disclosed figure is not independently audited. " * 4,
        content_depth="PARTIAL_CONTENT", metadata={"read_success": True,
            "page_metadata": {"body_quality": {"body_kind": "ARTICLE_BODY", "basis": "OBSERVED_DOCUMENT_STRUCTURE"}}}, **kwargs)


def test_candidate_snippet_is_not_captured_text_or_article():
    source = EvidenceItem(id="native", canonical_url="https://publisher.example/news/story",
        snippet="Cedar reportedly announced new financial results.", content="Search index summary", content_depth="SNIPPET")
    pool = RawAcquisitionPool("case")
    pool.add_capture(source)
    record = pool.get("native")
    assert record["discovery_snippet"] == source.snippet
    assert record["readable_text"] == "" and record["acquired_at"] is None
    assert pool.stats()["article_bodies"] == 0 and pool.stats()["reads_attempted"] == 0
    with pytest.raises(ValueError, match="cannot be qualified"):
        pool.mark_qualification("native", "QUALIFIED")


@pytest.mark.parametrize("depth,url,meta,expected", [
    ("SNIPPET", "https://p.example/story", {}, "DISCOVERY_LEAD"),
    ("PARTIAL_CONTENT", "https://p.example/news", {"page_metadata": {"content_scope": "FEED_INDEX"}}, "SOURCE_INDEX"),
    ("PARTIAL_CONTENT", "https://p.example/", {}, "PUBLISHER_HOMEPAGE"),
    ("FEED_ENTRY_CONTENT", "https://p.example/item", {}, "FEED_ENTRY"),
    ("FULL_ARTICLE", "https://p.example/article", {"page_metadata": {"body_quality": {"body_kind": "ARTICLE_BODY"}}}, "ARTICLE_BODY"),
    ("REGULATORY_FILING", "https://p.example/filing", {}, "OFFICIAL_DOCUMENT"),
    ("STRUCTURED_PUBLIC_DATA", "https://p.example/data", {}, "STRUCTURED_PUBLIC_DATA"),
    ("SOCIAL_POST", "https://p.example/post/1", {}, "COMMUNITY_POST"),
    ("PARTIAL_CONTENT", "https://en.wikipedia.org/wiki/Cedar", {}, "BACKGROUND_REFERENCE"),
])
def test_all_nonfailure_source_categories_are_distinct(depth, url, meta, expected):
    source = captured(url=url)
    source.content_depth, source.metadata = depth, {"read_success": True, **meta}
    pool = RawAcquisitionPool("typed")
    pool.add_capture(source, source_type="ARTICLE_BODY")
    assert pool.get("source")["source_type"] == expected
    assert set(type_.value for type_ in RawSourceType) == {
        "DISCOVERY_LEAD", "SOURCE_INDEX", "PUBLISHER_HOMEPAGE", "FEED_ENTRY", "ARTICLE_BODY",
        "OFFICIAL_DOCUMENT", "STRUCTURED_PUBLIC_DATA", "COMMUNITY_POST", "BACKGROUND_REFERENCE", "BLOCKED_OR_FAILED"}


def test_native_ids_and_canonical_aliases_preserve_distinct_urls():
    pool = RawAcquisitionPool("alias")
    a = EvidenceItem(id="native-first", canonical_url="https://EXAMPLE.com:443#top")
    b = EvidenceItem(id="native-second", canonical_url="https://example.com/")
    assert pool.add_candidate(a, "q1") == pool.add_candidate(b, "q2") == "native-first"
    assert pool.get("native-second")["source_id"] == "native-first"
    assert pool.get("native-first")["query_ids"] == ["q1", "q2"]
    assert a.canonical_url == "https://EXAMPLE.com:443#top"
    assert pool.add_candidate(EvidenceItem(id="native-first", canonical_url="https://example.com/?v=2")) != "native-first"
    assert pool.stats()["candidate_urls"] == 2


def test_capture_hash_bytes_words_exact_duplicates_and_qualifications():
    pool = RawAcquisitionPool("duplicates")
    a, b = captured("one"), captured("two", "https://another.example/reprint")
    before = a.to_dict()
    pool.add_capture(a, "query-a")
    pool.add_capture(b, "query-b")
    record = pool.get("one")
    assert record["raw_content_hash"] == hashlib.sha256(a.content.encode()).hexdigest()
    assert record["word_count"] == len(a.content.split())
    assert record["utf8_bytes"] == len(a.content.encode())
    assert pool.get("two")["duplicate_of"] == "one"
    assert pool.get("two")["readable_text"] == b.content
    assert a.to_dict() == before
    assert pool.stats()["article_bodies"] == 1 and pool.stats()["duplicate_captures"] == 1
    assert pool.mark_qualification("one", "QUALIFIED", ["relevant observed passage"], useful_words=20)
    assert pool.stats()["qualified_source_count"] == 1 and pool.stats()["relevant_words"] == 20
    assert pool.stats()["publisher_independence"] == "NOT_ESTABLISHED"
    with pytest.raises(ValueError):
        pool.mark_qualification("two", "QUALIFIED")


def test_changed_same_url_capture_preserves_original_revision():
    pool = RawAcquisitionPool("revisions")
    source = captured()
    pool.add_capture(source)
    first = source.content
    source.content = "The source corrected the earlier revenue statement. " * 5
    pool.add_capture(source)
    record = pool.get("source")
    assert record["readable_text"] == source.content
    assert record["prior_captures"][0]["readable_text"] == first
    assert record["read_attempts"] == 2
    assert pool.stats()["article_bodies"] == 1


def test_unknown_partial_page_is_retained_without_counting_as_article():
    source = captured()
    source.metadata = {"read_success": True, "page_metadata": {"body_quality": {"body_kind": "UNCLASSIFIED_PAGE"}}}
    pool = RawAcquisitionPool("unclassified")
    pool.add_capture(source)
    assert pool.get("source")["readable_text"] == source.content
    assert pool.stats()["article_bodies"] == 0
    with pytest.raises(ValueError):
        pool.mark_qualification("source", "QUALIFIED")


def test_candidate_content_without_acquisition_marker_is_not_a_capture():
    source = captured()
    source.metadata.pop("read_success")
    pool = RawAcquisitionPool("not-yet-read")
    pool.add_capture(source)
    assert pool.get("source")["readable_text"] == ""
    assert pool.stats()["successful_captures"] == 0


def test_conflicting_publication_declarations_survive_offline_reconciliation():
    from backend.services.research.body_context import reconcile_captured_context
    source = captured(published_at="2026-10-20")
    source.metadata["page_metadata"].update({"published": "2026-10-20", "publication_metadata_conflict": True,
        "publication_observations": [{"value": "2026-10-20", "source": "META"}, {"value": "2020-01-01", "source": "JSONLD"}]})
    pool = RawAcquisitionPool("conflict")
    pool.add_capture(source)
    original = pool.export()
    imported = RawAcquisitionPool.from_export(original)
    restored = imported.to_evidence_items()[0]
    reconcile_captured_context(restored)
    assert restored.published_at == ""
    assert restored.metadata["page_metadata"]["publication_metadata_conflict"] is True
    assert len(restored.metadata["page_metadata"]["publication_observations"]) == 2
    assert pool.get("source")["published_at"] is None
    assert original["sources"][0]["qualification_status"] == "PENDING"


def test_reconstructed_capture_preserves_recorded_clock_and_unknown_stays_unknown():
    pool = RawAcquisitionPool("clock")
    pool.add_capture(captured())
    original = pool.export()
    original["sources"][0]["discovered_at"] = "2026-10-21T04:49:24+00:00"
    original["sources"][0]["acquired_at"] = "2026-10-21T04:49:29+00:00"
    item = RawAcquisitionPool.from_export(original).to_evidence_items()[0]
    assert item.discovered_at == "2026-10-21T04:49:24+00:00"
    assert item.metadata["acquired_at"] == "2026-10-21T04:49:29+00:00"
    original["sources"][0]["discovered_at"] = None
    original["sources"][0]["acquired_at"] = None
    item = RawAcquisitionPool.from_export(original).to_evidence_items()[0]
    assert item.discovered_at == ""
    assert item.metadata["acquired_at"] is None


def test_wrapper_replacement_keeps_native_id_and_both_observed_locators():
    source = captured(url="https://news.google.com/rss/articles/opaque")
    pool = RawAcquisitionPool("wrapper")
    pool.add_candidate(source)
    old_url = source.canonical_url
    source.canonical_url = "https://publisher.example/news/earnings"
    source.metadata["discovery_url"] = old_url
    source.metadata["wrapper_resolution"] = {"selected_url": source.canonical_url}
    assert pool.add_capture(source) == "source"
    record = pool.get("source")
    assert record["source_url"] == source.canonical_url
    assert record["source_urls"] == [old_url, source.canonical_url]
    assert pool.stats()["source_count"] == 1


def test_body_revision_does_not_leave_stale_duplicate_ownership():
    pool = RawAcquisitionPool("revision-duplicate")
    first, second = captured("one"), captured("two", "https://b.example/article")
    pool.add_capture(first)
    pool.add_capture(second)
    assert pool.get("two")["duplicate_of"] == "one"
    first.content = "A later independent source correction reported new figures with explicit caveats. " * 5
    pool.add_capture(first)
    assert pool.get("two")["duplicate_of"] is None
    assert pool.stats()["article_bodies"] == 2


def test_failed_attempt_has_precise_category_and_cannot_erase_existing_capture():
    pool = RawAcquisitionPool("failure")
    source = captured()
    pool.add_failure(source, "HTTP_FAILURE", "HTTP 403", http_status=403)
    assert pool.get("source")["source_type"] == "BLOCKED_OR_FAILED"
    assert pool.get("source")["errors"][0]["http_status"] == 403
    pool.add_capture(source)
    pool.add_failure(source, "TIMEOUT", "Bounded read expired")
    assert pool.get("source")["readable_text"] == source.content
    assert pool.get("source")["extraction_status"] == "SUCCESS"
    assert pool.stats()["failed_reads_by_cause"] == {"HTTP_FAILURE": 1, "TIMEOUT": 1}


def test_failure_diagnostic_redacts_credential_fields_and_authentication():
    pool = RawAcquisitionPool("diagnostic")
    pool.add_failure(captured(), "HTTP_FAILURE", "HTTP 403 https://p.example/a?api_key=hidden Authorization: Bearer private-token")
    detail = pool.get("source")["errors"][0]["detail"]
    assert "hidden" not in detail and "private-token" not in detail
    assert "HTTP 403" in detail and "[REDACTED]" in detail


def test_storage_caps_never_silently_truncate_a_body():
    pool = RawAcquisitionPool("bounded", max_records=1, max_source_bytes=10)
    source = captured()
    pool.add_capture(source)
    assert pool.get("source")["readable_text"] == ""
    assert pool.get("source")["source_type"] == "BLOCKED_OR_FAILED"
    assert pool.stats()["dropped_by_limit"]["SOURCE_BYTES"] == 1
    assert pool.add_candidate(captured("other", "https://other.example/article")) is None
    assert pool.stats()["dropped_by_limit"]["SOURCE_COUNT"] == 1
    assert pool.stats()["article_bodies"] == 0


def test_byte_cap_and_secret_locators_do_not_enter_buffer():
    pool = RawAcquisitionPool("small", max_bytes=2000)
    source = captured()
    pool.add_capture(source)
    assert pool.stats()["storage_bytes"] < 2000
    assert pool.stats()["dropped_by_limit"]["POOL_BYTES"] >= 1
    for url in ("https://name:password@p.example/article", "https://p.example/article?api_key=value", "file:///private"):
        assert pool.add_candidate(url) is None
    assert pool.stats()["dropped_by_limit"]["INVALID_OR_SENSITIVE_URL"] == 3


def test_import_reprocesses_without_trusting_prior_qualification_or_cleanup_ownership():
    pool = RawAcquisitionPool("roundtrip")
    source = captured()
    pool.add_capture(source)
    pool.mark_qualification("source", "QUALIFIED", useful_words=10)
    path = pool.save_temporary()
    try:
        assert path.exists() and path.parent.name.startswith("aegis-raw-pool-")
        loaded = RawAcquisitionPool.load(path)
        assert loaded.get("source")["readable_text"] == source.content
        assert loaded.get("source")["qualification_status"] == "PENDING"
        assert loaded.get("source")["previous_qualification_status"] == "QUALIFIED"
        assert loaded.cleanup() is False and path.exists()
        assert loaded.stats()["qualified_source_count"] == 0
        assert loaded.stats()["acquisition_mode"] == "OFFLINE_REPROCESSING"
        restored = list(loaded.iter_evidence())
        assert len(restored) == 1 and restored[0].content == source.content
        assert restored[0].id == "source"
        assert restored[0].metadata["page_metadata"]["body_quality"]["body_kind"] == "ARTICLE_BODY"
        assert pool.save_temporary() == path
    finally:
        assert pool.cleanup()
    assert not path.exists()


def test_import_detects_changed_text_and_does_not_edit_input(tmp_path):
    pool = RawAcquisitionPool("tamper")
    pool.add_capture(captured())
    payload = pool.export()
    payload["sources"][0]["readable_text"] += " edited"
    path = tmp_path / "pool.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    old = path.read_bytes()
    with pytest.raises(ValueError, match="hash mismatch"):
        RawAcquisitionPool.load(path)
    assert path.read_bytes() == old


def test_import_rejects_forged_word_counts_and_overlong_history(tmp_path):
    pool = RawAcquisitionPool("import-validation")
    pool.add_capture(captured())
    payload = pool.export()
    path = tmp_path / "counts.json"
    payload["sources"][0]["word_count"] += 100
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="counts"):
        RawAcquisitionPool.load(path)
    payload = pool.export()
    payload["sources"][0]["aliases"] = ["untrusted"] * 33
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="history"):
        RawAcquisitionPool.load(path)


def test_cleanup_preserves_unexpected_user_files():
    pool = RawAcquisitionPool("cleanup")
    path = pool.save_temporary()
    unexpected = Path(path.parent / "keep-user-data.txt")
    unexpected.write_text("user data", encoding="utf-8")
    try:
        with pytest.raises(ValueError, match="Unexpected files"):
            pool.cleanup()
        assert path.exists() and unexpected.read_text(encoding="utf-8") == "user data"
    finally:
        unexpected.unlink()  # Only this exact file created by this test.
        pool.cleanup()


def test_export_without_text_retains_diagnostics_not_content():
    pool = RawAcquisitionPool("display")
    pool.add_capture(captured())
    record = pool.export(include_text=False)["sources"][0]
    assert "readable_text" not in record and "raw_text" not in record
    assert record["raw_content_hash"] and record["word_count"] > 0
    assert pool.get("source")["readable_text"]


def test_explicit_ambiguous_alias_import_excludes_joins_preserving_hashes_and_ids():
    import copy
    pool = RawAcquisitionPool("alias-rescue")
    first, second = captured("first"), captured("second", "https://other.example/story")
    pool.add_capture(first)
    second.content = "Cedar Instruments announced a separate audited filing, which did not verify the earlier article. " * 4
    pool.add_capture(second)
    payload = pool.export()
    payload["sources"][0]["aliases"] = ["native-ambiguous"]
    payload["sources"][1]["aliases"] = ["native-ambiguous"]
    original = copy.deepcopy(payload)
    with pytest.raises(ValueError, match="Conflicting source alias"):
        RawAcquisitionPool.from_export(payload)
    imported = RawAcquisitionPool.from_export(payload, allow_ambiguous_aliases=True)
    assert payload == original
    assert imported.get("native-ambiguous") is None
    assert imported.get("first")["raw_content_hash"] == payload["sources"][0]["raw_content_hash"]
    assert imported.get("second")["source_url"] == payload["sources"][1]["source_url"]
    assert imported.export()["ambiguous_aliases"] == [{"alias": "native-ambiguous", "source_ids": ["first", "second"], "excluded_from_alias_lookup": True}]
    assert not imported.mark_qualification("native-ambiguous", "REJECTED")
    assert imported.mark_qualification("first", "QUALIFIED", useful_words=10)
    # Explicit alias rescue never weakens integrity or identity validation.
    tampered = copy.deepcopy(payload)
    tampered["sources"][0]["readable_text"] += " tampered"
    with pytest.raises(ValueError, match="hash mismatch"):
        RawAcquisitionPool.from_export(tampered, allow_ambiguous_aliases=True)
    duplicate_id = copy.deepcopy(payload)
    duplicate_id["sources"][1]["source_id"] = "first"
    with pytest.raises(ValueError, match="Duplicate ID"):
        RawAcquisitionPool.from_export(duplicate_id, allow_ambiguous_aliases=True)
    duplicate_url = copy.deepcopy(payload)
    duplicate_url["sources"][1]["source_url"] = payload["sources"][0]["source_url"]
    with pytest.raises(ValueError, match="Duplicate canonical source"):
        RawAcquisitionPool.from_export(duplicate_url, allow_ambiguous_aliases=True)


def test_alias_collision_with_canonical_id_is_not_used_as_an_alias_join():
    pool = RawAcquisitionPool("canonical-collision")
    pool.add_capture(captured("first"))
    pool.add_capture(captured("second", "https://other.example/story"))
    payload = pool.export()
    payload["sources"][1]["aliases"] = ["first"]
    with pytest.raises(ValueError, match="Conflicting source alias"):
        RawAcquisitionPool.from_export(payload)
    imported = RawAcquisitionPool.from_export(payload, allow_ambiguous_aliases=True)
    assert imported.get("first")["source_id"] == "first"  # Unique raw ID, never second's native alias.
    assert "first" not in imported._aliases
    assert imported.export()["ambiguous_aliases"][0]["source_ids"] == ["first", "second"]


def test_observed_transport_snapshot_preserves_boundary_proof_without_secrets():
    pool = RawAcquisitionPool("transport")
    source = captured()
    original_raw_hash = "a" * 64
    source.metadata["transport"] = {
        "endpoint": "https://publisher.example/reports/final",
        "requested_endpoint": source.canonical_url,
        "redirect_chain": [source.canonical_url, "https://publisher.example/private?token=secret", "https://publisher.example/reports/final"],
        "raw_body_sha256": original_raw_hash, "http_status": 200,
        "raw_body_bytes": 7452, "decoded_body_bytes": 8312, "network_latency_ms": 16.2,
        "network_observed_this_attempt": True, "content_type": "text/html", "headers": {"Authorization": "Bearer private"},
        "cookie": "sensitive", "api_key": "sensitive"}
    pool.add_capture(source)
    record = pool.get("source")
    assert record["source_url"] == source.canonical_url
    assert record["actual_final_url"] == source.metadata["transport"]["endpoint"]
    assert record["transport"]["raw_body_sha256"] == original_raw_hash
    assert record["transport"]["raw_body_bytes"] == 7452
    assert record["transport"]["http_status"] == 200
    assert "headers" not in record["transport"] and "cookie" not in record["transport"]
    assert "secret" not in json.dumps(record["transport"])
    assert len(record["transport"]["redirect_chain"]) == 2
    restored = RawAcquisitionPool.from_export(pool.export()).to_evidence_items()[0]
    assert restored.metadata["transport"] == record["transport"]
