"""Opt-in live extraction API smoke; retains metrics, not public reply bodies."""
import argparse
import json
import os
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--allow-live", action="store_true")
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    if not args.allow_live:
        parser.error("Requires --allow-live")
    args.output_root.mkdir(parents=True, exist_ok=False)
    rows = []
    with tempfile.TemporaryDirectory(prefix="aegis-phase9-source-api-") as state:
        os.environ["SQLITE_DB_PATH"] = str(Path(state) / "aegis.db")
        os.environ["AEGIS_DOSSIER_DIR"] = str(Path(state) / "dossiers")
        os.environ["AEGIS_MOCK_LLM"] = "false"
        from fastapi.testclient import TestClient
        from backend.main import app
        # Do not run application lifespan/dashboard background acquisition.
        client = TestClient(app)
        for platform, operation, query in (
            ("hackernews", "read", "8863"),
            ("stackexchange", "read", "231767"),
            ("twitter", "status", "https://x.com/jack/status/20"),
            ("reddit", "read", "https://www.reddit.com/r/IAmA/comments/z1c9z/i_am_barack_obama/"),
        ):
            response = client.post("/api/agent-reach/extract", json={
                "platform": platform, "operation": operation, "query": query, "mode": "deep", "limit": 1,
            })
            body = response.json()
            evidence = body.get("evidence") or []
            rows.append({"platform": platform, "operation": operation, "http_status": response.status_code,
                         "status": body.get("status"), "runtime_reason": body.get("runtime_reason"),
                         "network_observed": body.get("network_observed"), "returned_records": len(evidence),
                         "inspected_records": sum(bool(item.get("extraction")) for item in evidence),
                         "captured_chars": sum((item.get("extraction") or {}).get("captured_chars", 0) for item in evidence),
                         "text_metrics": body.get("inspection_summary"),
                         "claim_support": body.get("claim_support"), "source_completeness": body.get("source_completeness")})
        client.close()
    report = {"scope": "Real FastAPI extraction routes, public source probes; no LLM call or full response retention",
              "records": rows, "all_sources_acquired": all(row["returned_records"] > 0 for row in rows),
              "reddit_approved_access_flag": os.getenv("REDDIT_APPROVED_ACCESS", "false").lower() in {"true", "1", "yes"},
              "access_note": "Existing application configuration; flag presence is not independent provider authorization",
              "claim_accuracy": None}
    (args.output_root / "summary.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 1 if any(row["http_status"] != 200 for row in rows) else 0


if __name__ == "__main__":
    raise SystemExit(main())
