"""Regression tests for the read-only historical dossier inventory."""

import json

import pytest

from scripts.validation.inventory_historical_dossiers import (
    _write_exclusively,
    inventory_archive,
)


def test_inventory_classifies_malformed_files_and_preserves_archive(tmp_path):
    archive = tmp_path / "archive"
    backup = tmp_path / "backup"
    archive.mkdir()
    backup.mkdir()
    valid = archive / "valid.json"
    malformed = archive / "broken.json"
    valid.write_text('{"status": "ok"}\n', encoding="utf-8")
    malformed.write_text('{"status": ', encoding="utf-8")
    (backup / "broken.json").write_text('{"status": "recovered"}\n', encoding="utf-8")
    before = {path.name: path.read_bytes() for path in archive.iterdir()}

    report = inventory_archive(archive, candidate_roots=[backup])

    assert report["status"] == "RECOVERY_ASSESSMENT_REQUIRED"
    assert report["summary"] == {
        "total_json_files": 2,
        "valid_json_files": 1,
        "malformed_json_files": 1,
        "valid_recovery_candidates": 1,
        "archive_bytes_unchanged": True,
    }
    finding = report["malformed_files"][0]
    assert finding["error_type"] == "JSONDecodeError"
    assert finding["line"] == 1
    assert finding["recovery_candidates"][0]["status"] == "VALID_JSON"
    assert {path.name: path.read_bytes() for path in archive.iterdir()} == before


def test_inventory_report_output_is_exclusive(tmp_path):
    output = tmp_path / "inventory.json"
    report = {"status": "test"}
    _write_exclusively(output, report)
    assert json.loads(output.read_text(encoding="utf-8")) == report
    with pytest.raises(FileExistsError):
        _write_exclusively(output, report)
