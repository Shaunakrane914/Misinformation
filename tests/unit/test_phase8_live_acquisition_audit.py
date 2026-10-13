"""Offline contracts for the Phase 8A live probe runner."""

from types import SimpleNamespace

from scripts.audits.run_phase8_live_acquisition_audit import (
    PROBES,
    PROTECTED_OPERATIONS,
    _aggregate,
    classify_probe,
    consolidate_run_records,
)


def _fragment(depth: str, mode: str = "direct_api"):
    return SimpleNamespace(content_depth=depth, retrieval_mode=mode)


def test_every_protected_operation_has_three_distinct_live_probe_scenarios():
    grouped = {
        operation: [probe for probe in PROBES if probe.operation == operation]
        for operation in PROTECTED_OPERATIONS
    }
    assert set(grouped) == set(PROTECTED_OPERATIONS)
    assert all(len(probes) == 3 for probes in grouped.values())
    assert all(len({probe.scenario for probe in probes}) == 3 for probes in grouped.values())
    assert all(probe.protected for probes in grouped.values() for probe in probes)


def test_phase8_classification_does_not_promote_discovery_or_feed_summaries():
    telemetry = {"status": "SUCCESS", "http_statuses": []}
    assert classify_probe(
        telemetry=telemetry,
        fragments=[_fragment("INDEX_SNIPPET", "web_search_index")],
        missing_is_not_found=False,
    ) == "SEARCH_DISCOVERY_ONLY"
    assert classify_probe(
        telemetry=telemetry,
        fragments=[_fragment("FEED_ENTRY_SUMMARY", "rss_feed")],
        missing_is_not_found=False,
    ) == "SYNDICATED_SUMMARY"
    assert classify_probe(
        telemetry=telemetry,
        fragments=[_fragment("METADATA", "rss_feed")],
        missing_is_not_found=False,
    ) == "DIRECT_METADATA"
    assert classify_probe(
        telemetry=telemetry,
        fragments=[_fragment("VIDEO_METADATA")],
        missing_is_not_found=False,
    ) == "DIRECT_METADATA"


def test_phase8_classification_preserves_failure_semantics():
    assert classify_probe(
        telemetry={"status": "AUTH_REQUIRED", "http_statuses": []},
        fragments=[], missing_is_not_found=False,
    ) == "AUTH_REQUIRED"
    assert classify_probe(
        telemetry={"status": "FAILED", "http_statuses": [429]},
        fragments=[], missing_is_not_found=False,
    ) == "RATE_LIMITED"
    assert classify_probe(
        telemetry={"status": "FAILED", "http_statuses": [403], "rate_limit_remaining": 0},
        fragments=[], missing_is_not_found=False,
    ) == "RATE_LIMITED"
    assert classify_probe(
        telemetry={"status": "FAILED", "http_statuses": [404]},
        fragments=[], missing_is_not_found=True,
    ) == "NOT_FOUND"
    assert classify_probe(
        telemetry={"status": "FAILED", "http_statuses": [], "error": "video unavailable"},
        fragments=[], missing_is_not_found=True,
    ) == "NOT_FOUND"
    assert classify_probe(
        telemetry={"status": "FAILED", "http_statuses": [], "error": "invalid JSON parse"},
        fragments=[], missing_is_not_found=False,
    ) == "PARSER_FAILURE"
    assert classify_probe(
        telemetry={"status": "SUCCESS", "http_statuses": [200], "provider_status": "EMPTY"},
        fragments=[], missing_is_not_found=False,
    ) == "EMPTY_RESULT"
    assert classify_probe(
        telemetry={"status": "SUCCESS", "http_statuses": [200], "provider_status": "EMPTY"},
        fragments=[], missing_is_not_found=True,
    ) == "NOT_FOUND"


def test_acceptance_requires_live_usable_output_for_every_protected_operation():
    complete = [
        {
            "operation": operation,
            "classification": "DIRECT_METADATA",
            "live_verified": True,
            "failure_reason": None,
        }
        for operation in PROTECTED_OPERATIONS
    ]
    assert _aggregate(complete)["gate"] == "PASS"
    complete[0] = {
        **complete[0], "classification": "UNVERIFIED", "live_verified": False,
    }
    result = _aggregate(complete)
    assert result["gate"] == "PARTIAL"
    assert PROTECTED_OPERATIONS[0] in result["not_live_verified_operations"]


def test_consolidation_replaces_an_operation_as_a_whole(tmp_path):
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()
    (first / "probe_records.jsonl").write_text(
        '{"operation":"github.read","scenario":"old"}\n'
        '{"operation":"web.read","scenario":"keep"}\n',
        encoding="utf-8",
    )
    (second / "probe_records.jsonl").write_text(
        '{"operation":"github.read","scenario":"new-a"}\n'
        '{"operation":"github.read","scenario":"new-b"}\n',
        encoding="utf-8",
    )
    records = consolidate_run_records([first, second])
    github = [item for item in records if item["operation"] == "github.read"]
    assert [item["scenario"] for item in github] == ["new-a", "new-b"]
    assert any(item["operation"] == "web.read" for item in records)
