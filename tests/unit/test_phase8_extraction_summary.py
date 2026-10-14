"""The Phase 8B report must not infer missing fields or rewrite old evidence."""

import json
import subprocess
import sys
from pathlib import Path


def test_summary_prefers_newest_matching_probe_and_refuses_overwrite(tmp_path):
    root = Path(__file__).resolve().parents[2]
    script = root / "scripts/audits/summarize_phase8_extraction.py"
    old = tmp_path / "old.jsonl"
    new = tmp_path / "new.jsonl"
    output = tmp_path / "summary.json"
    base = {
        "operation": "github.read", "scenario": "common", "live_verified": True,
        "classification": "DIRECT_METADATA", "item_count": 1,
        "relevant_text_chars": 10, "latency_ms": 20,
        "content_depths": ["METADATA"],
        "provenance": {"normalized_evidence_samples": [{
            "title": "Repository", "canonical_url": "https://github.com/owner/repo",
            "published": "", "backend_id": "GitHub REST API",
            "content_depth": "METADATA",
        }]},
    }
    old.write_text(json.dumps(base) + "\n", encoding="utf-8")
    improved_sample = dict(base["provenance"]["normalized_evidence_samples"][0],
                           author="", content_chars=100,
                           populated_metadata_field_names=["readme_sha"])
    improved = dict(base, classification="DIRECT_PARTIAL_CONTENT", relevant_text_chars=100,
                    provenance={"normalized_evidence_samples": [improved_sample]})
    new.write_text(json.dumps(improved) + "\n", encoding="utf-8")
    command = [
        sys.executable, str(script), "--probe-records", str(old),
        "--probe-records", str(new), "--output", str(output),
    ]
    first = subprocess.run(command, cwd=root, text=True, capture_output=True, check=False)
    assert first.returncode == 0, first.stderr
    report = json.loads(output.read_text(encoding="utf-8"))
    row = report["operations"]["github.read"]
    assert row["scenario_count"] == 1
    assert row["mean_relevant_chars_per_successful_item"] == 100
    assert row["normalized_field_population_rate"]["published"] == 0.0
    assert row["normalized_field_population_rate"]["author"] == 0.0
    assert row["important_field_population"]["metadata.readme_sha"] == {
        "populated": 1, "measured_samples": 1, "population_rate": 1.0,
    }
    assert row["important_field_population"]["author"]["population_rate"] == 0.0
    assert report["operations"]["web.read"]["important_field_population"]["page.tables"] == {
        "populated": 0, "measured_samples": 0, "population_rate": None,
    }
    assert len(report["operations"]) == 16
    module_output = tmp_path / "module-summary.json"
    module_command = [
        sys.executable, "-m", "scripts.audits.summarize_phase8_extraction",
        "--probe-records", str(new), "--output", str(module_output),
    ]
    module_run = subprocess.run(module_command, cwd=root, text=True,
                                capture_output=True, check=False)
    assert module_run.returncode == 0, module_run.stderr
    assert json.loads(module_output.read_text(encoding="utf-8"))["operations"]["github.read"]["live_success_count"] == 1
    second = subprocess.run(command, cwd=root, text=True, capture_output=True, check=False)
    assert second.returncode != 0
    assert "already exists" in second.stderr
