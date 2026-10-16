"""Opt-in, bounded real research probes. No model or response fixtures.

Targets are supplied separately from exact claims. Reference URLs are acquisition
leads, not injected passages or ground-truth authority. Labels are source-
adjudicated hypotheses, not human-reviewed truth or population accuracy.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import logging
import os
from pathlib import Path
import subprocess
import sys
import time

from dotenv import dotenv_values


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--allow-live", action="store_true", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--env-file", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--case-ids", nargs="+", help="Explicit diagnostic recheck subset; not a replacement for the full matrix")
    args = parser.parse_args()
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=False)
    root = args.repo_root.resolve()
    sys.path.insert(0, str(root))
    values = dotenv_values(args.env_file)
    allowed = ("GEMINI_API_KEY", "GEMINI_KEY_", "GROQ_API_KEY", "YF_API_KEY", "AGENT_REACH_",
               "REDDIT_", "AEGIS_REDDIT_", "EXA_API_KEY", "TAVILY_API_KEY", "BRAVE_API_KEY",
               "FACTCHECK_API_KEY", "SEC_USER_AGENT", "YOUTUBE_API_KEY", "GITHUB_TOKEN", "JINA_API_KEY")
    for key, value in values.items():
        os.environ[key] = str(value or "") if key.startswith(allowed) else ""
    for key in list(os.environ):
        if key.startswith(("SUPABASE_", "TWILIO_", "SMTP_", "SENDGRID_", "RENDER_", "CLOUDFLARE_")):
            os.environ[key] = ""
    os.environ.update(SQLITE_DB_PATH=str(output / "aegis.db"), AEGIS_SQLITE_PATH=str(output / "aegis.db"),
                      AEGIS_DOSSIER_DIR=str(output / "dossiers"), AEGIS_MOCK_LLM="false",
                      ENVIRONMENT="development", AEGIS_ENV="development", RSS_INGESTION_ENABLED="false",
                      AEGIS_SOURCE_PLANNER_LLM_ENABLED="false", LLM_REQUEST_TIMEOUT="5", LLM_MAX_RETRIES="1")
    secrets = [str(value) for key, value in values.items() if value and len(str(value)) > 8
               and any(part in key.upper() for part in ("KEY", "TOKEN", "SECRET", "PASSWORD", "COOKIE"))]

    class RedactingFormatter(logging.Formatter):
        def format(self, record):
            text = super().format(record)
            for secret in secrets:
                text = text.replace(secret, "[REDACTED]")
            return text

    handler = logging.FileHandler(output / "backend.log", encoding="utf-8")
    handler.setFormatter(RedactingFormatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    logging.basicConfig(level=logging.INFO, handlers=[handler], force=True)
    from backend.services.research.research_engine import ResearchEngine
    from backend.services.research.research_models import ResearchRequest
    from backend.services.report_builder import ReportBuilder
    from backend.services.research.replay_ledger import replay_ledger, verify_dossier_integrity
    from scripts.audits.run_realworld_investigation_audit import sanitize_audit_data

    paper = "https://arxiv.org/abs/1706.03762"
    iphone = "https://www.apple.com/newsroom/2023/09/apple-debuts-iphone-15-and-iphone-15-plus/"
    acquisition = "https://news.microsoft.com/2016/12/08/microsoft-closes-acquisition-of-linkedin/"
    cases = [
        ("corporate_announcement", "Microsoft", "Microsoft completed its acquisition of LinkedIn in December 2016.", acquisition, "SUPPORTED"),
        ("false_financial", "Apple", "Apple quarterly net income was $900 billion in Q1 fiscal 2024.", "https://www.apple.com/newsroom/2024/02/apple-reports-first-quarter-results/", "REFUTED"),
        ("product_release", "Apple", "Apple announced iPhone 15 in September 2023.", iphone, "SUPPORTED"),
        ("outdated_news", "Microsoft", "Steve Ballmer is the current chief executive officer of Microsoft.", "https://news.microsoft.com/exec/satya-nadella/", "OUTDATED"),
        ("scientific_title_true", "arXiv", "The title of arXiv paper 1706.03762 is Attention Is All You Need.", paper, "SUPPORTED"),
        ("scientific_title_false", "arXiv", "The title of arXiv paper 1706.03762 is Recurrence Is All You Need.", paper, "REFUTED"),
        ("cybersecurity", "Apache", "NIST rated CVE-2021-44228 a CVSS score of 2.1.", "https://nvd.nist.gov/vuln/detail/CVE-2021-44228", "REFUTED"),
        ("impersonation_allegation", "Apple", "Apple's iPhone 15 announcement proves an impersonation ring was identified.", iphone, "INSUFFICIENT_EVIDENCE"),
        ("fabricated_quote", "Microsoft", 'Microsoft said "the Earth is flat" in its LinkedIn acquisition announcement.', acquisition, "INSUFFICIENT_EVIDENCE"),
        ("mixed_claim", "Apple", "Apple announced iPhone 15 in September 2023 and it has a physical keyboard.", iphone, "UNVERIFIED"),
        ("source_unavailable", "Example", "Example announced an acquisition in 2026.", "https://source-unavailable.invalid/announcement", "INSUFFICIENT_EVIDENCE"),
    ]
    payload = {"head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip(),
               "tracked_diff_sha256": hashlib.sha256(subprocess.check_output(["git", "diff"], cwd=root)).hexdigest(),
               "observed_at": datetime.now(timezone.utc).isoformat(), "scope": "Live ResearchEngine through immutable dossier and shared report, not HTTP/frontend acceptance",
               "source_passages_injected": False, "human_reviewed": False, "network_request_count": None,
               "labels": "Source-adjudicated diagnostic expectations, mixed/absence cases require human assessment",
               "cases": []}
    engine = ResearchEngine()
    if args.case_ids:
        unknown = set(args.case_ids) - {case[0] for case in cases}
        if unknown:
            parser.error("Unknown diagnostic case ID")
        cases = [case for case in cases if case[0] in args.case_ids]
    payload["selected_case_ids"] = [case[0] for case in cases]
    for code, entity, claim, url, expected in cases:
        start = time.perf_counter()
        request = ResearchRequest(target=entity, domain="general", agent_name="phase9_live_probe",
                                  source_url=url, timeout_seconds=15, deep_read_budget=3, max_candidates=20,
                                  extra_params={"claim_text": claim}, intent=claim)
        try:
            result = engine.investigate(request)
            dossier_id = result.telemetry.get("dossier_id")
            dossier = replay_ledger.get_dossier(dossier_id) if dossier_id else None
            report = ReportBuilder.from_scout_result(query=claim, scout_data={
                "sources": [item.to_dict() for item in result.evidence],
                "findings": [item.to_dict() for item in result.findings], "research_corpus": result.research_corpus,
                "deep_research_trace": result.telemetry}).to_dict()
            row = {"id": code, "claim": claim, "entity": entity, "lead_url": url, "diagnostic_expected": expected,
                   "seconds": round(time.perf_counter() - start, 3), "retained_records": len(result.evidence),
                   "words": sum(len((item.content or item.snippet).split()) for item in result.evidence),
                   "kb": round(sum(len((item.content or item.snippet).encode()) for item in result.evidence)/1000, 3),
                   "funnel": result.telemetry.get("funnel"), "dossier_id": dossier_id,
                   "dossier_integrity": verify_dossier_integrity(dossier) if dossier else None,
                   "report": report}
        except Exception as error:
            row = {"id": code, "claim": claim, "error_type": type(error).__name__,
                   "seconds": round(time.perf_counter()-start, 3)}
        payload["cases"].append(row)
        text = json.dumps(sanitize_audit_data(payload), ensure_ascii=False, indent=2)
        for secret in secrets:
            text = text.replace(secret, "[REDACTED]")
        (output / "summary.json").write_text(text, encoding="utf-8")
        print(json.dumps({key: value for key, value in row.items() if key not in {"report", "funnel"}}), flush=True)
    return 1 if any("error_type" in row for row in payload["cases"]) else 0


if __name__ == "__main__":
    raise SystemExit(main())
