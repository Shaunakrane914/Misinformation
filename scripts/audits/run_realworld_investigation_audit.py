"""Four-agent API audit separating execution, acquisition and research correctness.

Each API is called once. Live runs use temporary persistence and a new output directory.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import html
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time
import uuid

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

CASES = {
    "brandshield": ("/api/brandshield/scan", {"brand_name": "Microsoft", "query": "Microsoft impersonation phishing brand threats"}),
    "trending": ("/api/trending/scan", {"asset_name": "Microsoft", "query": "Microsoft recent technology announcements"}),
    "scout": ("/api/scout/analyze", {"ticker": "MSFT", "query": "Microsoft quarterly financial disclosures"}),
    "personal_watch": ("/api/personal/scan", {"name": "Satya Nadella", "query": "Satya Nadella recent public statements"}),
}
_SENSITIVE = {"key", "api_key", "token", "access_token", "authorization", "cookie", "password", "secret", "phone_number"}


def response_records(body):
    """Some agents expose a provider-summary mapping as sources, not records."""
    for key in ("evidence", "sources"):
        records = body.get(key)
        if isinstance(records, list) and records:
            return [item for item in records if isinstance(item, dict)]
    return []


def sanitize_audit_data(value):
    if isinstance(value, dict):
        return {str(k): "[REDACTED]" if str(k).lower() in _SENSITIVE or str(k).lower().endswith(("_api_key", "_token", "_secret")) else sanitize_audit_data(v) for k, v in value.items()}
    if isinstance(value, list):
        return [sanitize_audit_data(v) for v in value]
    if isinstance(value, str):
        value = re.sub(r"(?i)([?&](?:key|token|api_key|access_token)=)[^&#\s]+", r"\1[REDACTED]", value)
        value = re.sub(r"(?i)https?://[^/@\s]+:[^/@\s]+@", "https://[REDACTED]@", value)
        value = re.sub(r"\b(?:AIza[0-9A-Za-z_-]{20,}|ghp_[0-9A-Za-z]{20,})\b", "[REDACTED]", value)
        value = re.sub(r"\b\d{3}-\d{2}-\d{4}\b", "[REDACTED_SSN]", value)
        value = re.sub(r"\b(?:\+?1[-. ]?)?\(?[2-9]\d{2}\)?[-. ]?\d{3}[-. ]?\d{4}\b", "[REDACTED_PHONE]", value)
        value = re.sub(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", "[REDACTED_EMAIL]", value)
        return value
    return value


def summarize_response(status_code, body, elapsed):
    """Execution, acquisition, relevance and correctness are distinct observations."""
    records = response_records(body)
    valid = [e for e in records if isinstance(e, dict)]
    inspectable = [e for e in valid if e.get("url") or e.get("canonical_url")]
    retrieval = body.get("retrieval") or body.get("retrieval_stats") or {}
    return {
        "http_status": status_code, "latency_seconds": round(elapsed, 3),
        "execution": "PASS" if 200 <= status_code < 300 else "FAIL",
        "network_acquisition": "OBSERVED" if retrieval.get("network_observed") is True else "NOT_VERIFIED",
        "returned_record_count": len(valid), "inspectable_url_count": len(inspectable),
        "relevant_evidence": "NOT_INDEPENDENTLY_ADJUDICATED",
        "evidence_sufficiency": "NOT_VERIFIED", "conclusion_correctness": "NOT_VERIFIED",
        "independent_precision": None, "independent_recall": None,
        "coverage": "NO_RETURNED_EVIDENCE" if not valid else "REQUIRES_ADJUDICATION",
        "response": sanitize_audit_data(body),
    }


def render_report(payload):
    lines = [
        "# Four-agent API investigation audit", "",
        f"Commit: {payload['commit']}; dirty source: {payload['dirty']}.",
        f"Observed at: {payload['observed_at_utc']}. Overall research gate: **PARTIAL**.", "",
        "API execution, returned records and research correctness are assessed separately.",
        "Independent precision, recall, entailment and LLM-injection success require separate adjudication.", "",
        "| Agent | Execution | Returned records | URL-bearing records | Coverage | Correctness |",
        "|---|---|---:|---:|---|---|",
    ]
    for name, result in payload["agents"].items():
        lines.append(f"| {name} | {result['execution']} | {result['returned_record_count']} | {result['inspectable_url_count']} | {result['coverage']} | {result['conclusion_correctness']} |")
    for name, result in payload["agents"].items():
        lines.extend(["", f"## {name}", "", f"Exact request: {json.dumps(payload['requests'][name], ensure_ascii=True)}", ""])
        records = response_records(result["response"])
        if not records:
            lines.append("No evidence records returned. Evidence coverage is insufficient for an independently verified conclusion.")
        for item in records[:20]:
            if not isinstance(item, dict):
                continue
            title = html.escape(str(item.get("title") or "Title not supplied")).replace("|", "\\|").replace("\n", " ")
            url = item.get("url") or item.get("canonical_url") or ""
            excerpt = html.escape(str(item.get("relevant_excerpt") or item.get("content") or item.get("snippet") or "")[:700])
            lines.extend([f"- Returned record: {title}", f"  URL: {url}", f"  Depth: {item.get('content_depth', 'UNREPORTED')}; publication: {item.get('published_at', item.get('published', ''))}", f"  Retained passage: {excerpt.replace(chr(10), ' ')}"])
    lines.extend(["", "Complete sanitized API payloads are in summary.json. Claim-to-passage adjudication is required before a research PASS can be assigned.", ""])
    return sanitize_audit_data("\n".join(lines))


def run_investigation(output_root=None, cases=None):
    from fastapi.testclient import TestClient
    from backend.main import app
    from backend.services.gemini_service import gemini_service

    selected = cases or CASES
    root = Path(output_root) if output_root else ROOT_DIR / "artifacts" / "phase8_independent_investigations" / (datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M-%SZ") + "_" + uuid.uuid4().hex[:8])
    root.mkdir(parents=True, exist_ok=False)
    sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT_DIR, text=True).strip()
    dirty = bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT_DIR, text=True).strip())
    payload = {
        "observed_at_utc": datetime.now(timezone.utc).isoformat(), "commit": sha,
        "dirty": dirty, "scope": "Live acquisition through actual in-process FastAPI requests; temporary persistence",
        "llm_mock_mode": gemini_service.mock_mode, "agents": {},
        "requests": {name: request for name, (_, request) in selected.items()},
        "overall_research_gate": "PARTIAL", "prompt_injection_model_evaluation": "NOT_VERIFIED",
    }
    with TestClient(app) as client:
        for name, (route, request) in selected.items():
            started = time.monotonic()
            try:
                response = client.post(route, json=request)
                body = response.json()
                if not isinstance(body, dict):
                    body = {"error": "Unexpected response shape"}
                result = summarize_response(response.status_code, body, time.monotonic() - started)
            except Exception as exc:
                result = summarize_response(500, {"error_type": type(exc).__name__}, time.monotonic() - started)
            payload["agents"][name] = result
            print(f"{name}: execution={result['execution']} records={result['returned_record_count']} correctness=NOT_VERIFIED", flush=True)
    payload = sanitize_audit_data(payload)
    with (root / "summary.json").open("x", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=True)
    with (root / "report.md").open("x", encoding="utf-8") as handle:
        handle.write(render_report(payload))
    print(f"Evidence directory: {root}", flush=True)
    return payload


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--allow-live", action="store_true")
    parser.add_argument("--output-root", type=Path)
    parser.add_argument("--agents", default=",".join(CASES))
    parser.add_argument("--profile", choices=("microsoft", "apple"), default="microsoft")
    args = parser.parse_args()
    if not args.allow_live:
        parser.error("Use --allow-live for this network audit; offline regressions are separate.")
    selected = {name: CASES[name] for name in args.agents.split(",") if name in CASES}
    if args.profile == "apple":
        selected = {name: (route, {k: v.replace("Microsoft", "Apple").replace("MSFT", "AAPL").replace("Satya Nadella", "Tim Cook") if isinstance(v, str) else v for k, v in request.items()}) for name, (route, request) in selected.items()}
    if not selected:
        parser.error("No known agents selected")
    with tempfile.TemporaryDirectory(prefix="aegis-live-api-audit-") as storage:
        os.environ.update({
            "ENVIRONMENT": "development", "AEGIS_ENV": "development",
            "AEGIS_MOCK_LLM": "false", "RSS_INGESTION_ENABLED": "false",
            "SQLITE_DB_PATH": str(Path(storage) / "aegis.db"),
            "AEGIS_SQLITE_PATH": str(Path(storage) / "aegis.db"),
            "AEGIS_DOSSIER_DIR": str(Path(storage) / "dossiers"),
            "SUPABASE_URL": "", "SUPABASE_KEY": "", "SUPABASE_SERVICE_ROLE_KEY": "",
            "SUPABASE_ANON_KEY": "",
            "TWILIO_ACCOUNT_SID": "", "TWILIO_AUTH_TOKEN": "",
        })
        run_investigation(args.output_root, selected)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
