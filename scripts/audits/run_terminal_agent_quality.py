"""Terminal-first real local SSE investigations, then exact frontend replay.

Uses normal app routes with isolated persistence and no background ingestion or
notifications. Saved responses/events permit offline output review and browser
replay without reacquiring providers. Counts are not research acceptance.
"""
import argparse
import hashlib
import json
import logging
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from contextlib import ExitStack
from dataclasses import fields
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts.audits.resource_sampler import ResourceSampler  # noqa: E402
CASES = [(agent, query) for agent, queries in (
    ("scout", ("TATAMOTORS.NS", "INFY.NS", "AAPL")),
    ("trending", ("OpenAI", "NVIDIA", "electric vehicles")),
    ("brandshield", ("Nike", "Apple", "Tata Motors")),
    ("personal_watch", ("Sam Altman", "Tim Cook", "Satya Nadella")),
) for query in queries]


def fingerprint():
    digest = hashlib.sha256()
    for name in sorted(set(subprocess.check_output(["git", "ls-files", "--cached", "--others", "--exclude-standard", "backend", "frontend"], cwd=ROOT, text=True).splitlines())):
        path = ROOT / name
        if path.is_file():
            digest.update(name.encode())
            digest.update(path.read_bytes())
    return digest.hexdigest()


def parse_events(text):
    events = []
    for block in text.replace("\r\n", "\n").split("\n\n"):
        event = next((line[7:] for line in block.splitlines() if line.startswith("event: ")), None)
        data = "\n".join(line[6:] for line in block.splitlines() if line.startswith("data: "))
        if event and data:
            events.append({"event": event, "data": json.loads(data)})
    return events


def native_source_records(native):
    """Native agents also use 'evidence' for grouped/non-record metadata."""
    for key in ("evidence", "sources"):
        value = native.get(key)
        if isinstance(value, list):
            return [record for record in value if isinstance(record, dict)]
    return []


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--allow-live", action="store_true", required=True)
    parser.add_argument("--allow-live-ai", action="store_true", help="Separate opt-in; scraper checks use no AI credentials by default")
    parser.add_argument("--env-file", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--case", action="append", default=[], help="agent:input; otherwise fixed twelve")
    parser.add_argument("--query", action="append", default=[], help="Optional per-case query override; supply one per case, in case order")
    parser.add_argument("--case-manifest", type=Path, help="Explicit local cases: id, agent, input, query, optional category")
    parser.add_argument("--observe-website-http", action="store_true", help="Read-only transport/admission ledger; no extra requests")
    parser.add_argument("--capture-from", type=Path, help="Offline reprocessing of saved native responses; no provider acquisition")
    parser.add_argument("--timeout-seconds", type=float, help="Explicit research deadline for a bounded authorized audit")
    parser.add_argument("--max-deep-reads", type=int, help="Total deep-reader attempt allowance per case")
    parser.add_argument("--research-profile", choices=("QUICK", "STANDARD", "DEEP"), default="STANDARD")
    parser.add_argument("--max-http-admissions", type=int, help="Optional lower native HTTP cap; includes retries and redirects")
    parser.add_argument("--acquisition-controller", choices=("legacy", "interleaved_v1", "pipelined_v1"), default="legacy",
                        help="Explicit local experiment; preserves existing read/HTTP caps")
    args = parser.parse_args()
    profile_limits = {"QUICK": (60, 6), "STANDARD": (150, 14), "DEEP": (240, 24)}
    timeout_cap, read_cap = profile_limits[args.research_profile]
    if args.max_http_admissions is not None and not 1 <= args.max_http_admissions <= 120:
        parser.error("Native HTTP cap must be within 1..120")
    if args.timeout_seconds is not None and not 0 < args.timeout_seconds <= timeout_cap:
        parser.error("Audit timeout exceeds selected research profile")
    if args.max_deep_reads is not None and not 0 <= args.max_deep_reads <= read_cap:
        parser.error("Audit reads exceed selected research profile")
    if args.capture_from and args.allow_live_ai:
        parser.error("Saved-capture processing never permits live AI")
    if args.acquisition_controller != "legacy" and args.capture_from:
        parser.error("Historical capture mode does not exercise an experimental acquisition controller")
    cases = []
    for value in args.case:
        agent, _, query = value.partition(":")
        if agent not in {a for a, _ in CASES} or not query.strip() or len(query) > 200:
            parser.error("Invalid agent:input")
        cases.append((agent, query.strip()))
    cases = cases or CASES
    manifest = None
    if args.case_manifest:
        if args.case or args.query:
            parser.error("Case manifest cannot be combined with --case/--query")
        manifest = json.loads(args.case_manifest.read_text(encoding="utf-8"))
        if not isinstance(manifest, list) or not 1 <= len(manifest) <= 16:
            parser.error("Case manifest requires 1..16 explicit cases")
        for row in manifest:
            if (row.get("agent") not in {a for a, _ in CASES}
                    or not re.fullmatch(r"[A-Z][1-4]", row.get("id", ""))
                    or not isinstance(row.get("input"), str) or not 1 <= len(row["input"]) <= 80
                    or not isinstance(row.get("query"), str) or not 1 <= len(row["query"]) <= 2000):
                parser.error("Invalid explicit case")
        if len({r["id"] for r in manifest}) != len(manifest):
            parser.error("Case IDs must be unique")
        cases = [(r["agent"], r["input"]) for r in manifest]
    if args.allow_live_ai and len(cases) > 5:
        parser.error("AI-authorized batches are limited to five investigations")
    if args.query and len(args.query) != len(cases):
        parser.error("--query must be supplied once for every selected case")
    out = args.output_dir.resolve()
    out.mkdir(parents=True, exist_ok=False)
    from dotenv import dotenv_values
    values = dotenv_values(args.env_file)
    allowed = ("GEMINI_API_KEY", "GEMINI_KEY_", "GROQ_API_KEY", "YF_API_KEY", "AGENT_REACH_", "REDDIT_",
               "AEGIS_REDDIT_", "EXA_API_KEY", "TAVILY_API_KEY", "BRAVE_API_KEY", "FACTCHECK_API_KEY",
               "SEC_USER_AGENT", "YOUTUBE_API_KEY", "GITHUB_TOKEN", "JINA_API_KEY", "AEGIS_AI_POLICY_DB", "AEGIS_AI_DAILY_REQUEST_LIMIT", "LLM_ADVISORY_MODEL")
    ai_prefixes = ("GEMINI_", "GROQ_", "OPENAI_", "ANTHROPIC_")
    if not args.allow_live_ai:
        for key in list(os.environ):
            if key.startswith(ai_prefixes):
                os.environ[key] = ""
    for key, value in values.items():
        os.environ[key] = str(value or "") if key.startswith(allowed) and (args.allow_live_ai or not key.startswith(ai_prefixes)) else ""
    for key in list(os.environ):
        if key.startswith(("SUPABASE_", "TWILIO_", "SMTP_", "SENDGRID_", "RENDER_", "CLOUDFLARE_")):
            os.environ[key] = ""
    os.environ.update(SQLITE_DB_PATH=str(out / "aegis.db"), AEGIS_SQLITE_PATH=str(out / "aegis.db"),
                      AEGIS_DOSSIER_DIR=str(out / "dossiers"), AEGIS_MOCK_LLM="false",
                      ENVIRONMENT="development", AEGIS_ENV="development", RSS_INGESTION_ENABLED="false",
                      LLM_REQUEST_TIMEOUT="5", LLM_MAX_RETRIES="1")
    # Native-yield checks never consume an inherited paid-reader credential or
    # initialize unused optional monitoring, even if present in the parent shell.
    os.environ.update(FIRECRAWL_API_KEY="", FIRECRAWL_API_BASE_URL="https://api.firecrawl.dev",
                      FIRECRAWL_BASE_URL="", HUGINN_ENABLED="false", HUGINN_WEBHOOK_SECRET="",
                      HUGINN_DB_PATH=str(out / "huginn.db"))
    os.environ["AEGIS_RESEARCH_PROFILE"] = args.research_profile
    os.environ["AEGIS_ACQUISITION_CONTROLLER"] = args.acquisition_controller
    os.environ["AEGIS_RAW_POOL_PERSIST"] = "true"
    if args.max_http_admissions is not None:
        os.environ["AEGIS_HARVEST_HTTP_CAP"] = str(args.max_http_admissions)
    for prefix in ("SERVER_RESEARCH_", "LOCAL_RESEARCH_"):
        os.environ[prefix + "TIMEOUT"] = str(args.timeout_seconds if args.timeout_seconds is not None else timeout_cap)
        os.environ[prefix + "MAX_DEEP_READS"] = str(args.max_deep_reads if args.max_deep_reads is not None else read_cap)
        os.environ[prefix + "MAX_QUERIES"] = str({"QUICK": 24, "STANDARD": 60, "DEEP": 100}[args.research_profile])
    secrets = [str(v) for k, v in values.items() if v and len(str(v)) > 8 and
               any(s in k.upper() for s in ("KEY", "TOKEN", "SECRET", "PASSWORD", "COOKIE"))]

    def redact(text):
        for secret in secrets:
            text = text.replace(secret, "[REDACTED]")
        return re.sub(r"([?&](?:key|token|api_key)=)[^&\s\"\\]+", r"\1[REDACTED]", text, flags=re.I)

    def save(name, value):
        # Provider metadata can contain escaped UTF-16 surrogate code units.
        # ASCII JSON preserves them without a failed UTF-8 write losing proof.
        (out / name).write_text(redact(json.dumps(value, ensure_ascii=True, indent=2)), encoding="utf-8")

    class SafeFormatter(logging.Formatter):
        def format(self, record):
            return redact(super().format(record))

    handler = logging.FileHandler(out / "backend.log", encoding="utf-8")
    handler.setFormatter(SafeFormatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    logging.basicConfig(level=logging.INFO, handlers=[handler], force=True)
    if args.capture_from:
        from scripts.validation.isolated_runtime import block_live_network
        block_live_network()
    from fastapi.testclient import TestClient
    from backend.main import app
    from backend.core.settings import settings
    assert not settings.is_mock_llm and not settings.supabase_write_key and not settings.supabase_url
    if not args.allow_live_ai:
        assert not settings.gemini_api_keys
    from backend.infrastructure.llm.advisory_policy import call_count, observations
    run_stack = ExitStack()
    if os.name == "nt":
        # Keep this audit thread awake without changing the machine's power
        # plan. Release the execution-state request on normal/error closeout.
        import ctypes
        ctypes.windll.kernel32.SetThreadExecutionState(0x80000001)
        run_stack.callback(ctypes.windll.kernel32.SetThreadExecutionState, 0x80000000)
    model_check = {"status": "DISABLED", "model": settings.llm_advisory_model}
    if args.allow_live_ai:
        # Reuse the production runtime's bounded model check and persisted
        # UTC-day quota. A new audit must not open a fresh random quota bucket.
        from backend.infrastructure.llm.runtime_advisory import runtime_advisory_scope
        os.environ["AEGIS_LIVE_ADVISORY_ENABLED"] = "true"
        model_check = run_stack.enter_context(runtime_advisory_scope(settings))
        os.environ["AEGIS_SEARCH_ADVISOR_ENABLED"] = "true" if model_check["status"] == "ENABLED" else "false"
        os.environ["AEGIS_EVIDENCE_ADVISOR_ENABLED"] = "false"
        print(json.dumps({"advisory_model_check": model_check}), flush=True)
    initial_ai_count = call_count()
    # Deliberately no context manager: do not run app lifespan ingestion jobs.
    client = TestClient(app)
    routes = {"scout": ("scout/analyze", "ticker"), "trending": ("trending/scan", "query"),
              "brandshield": ("brandshield/scan", "brand_name"), "personal_watch": ("personal/scan", "name")}
    initial = fingerprint()
    summary = {"mode": "REAL_LOCAL_ASGI_SSE", "application_sha256": initial, "cases": [],
               "scope": "Normal local routes/provider acquisition, no browser; word counts are not evidence quality",
               "mock_llm": False, "live_ai_authorized": args.allow_live_ai}
    summary["acquisition_controller"] = args.acquisition_controller
    summary["requested_audit_bounds"] = {"research_timeout_seconds": args.timeout_seconds, "max_deep_reads": args.max_deep_reads, "research_profile": args.research_profile}
    summary["advisory_model_check"] = model_check
    if args.capture_from:
        summary.update(mode="OFFLINE_SAVED_CAPTURE_REPROCESS", scope="Current agent/API processing of saved source bytes; no fresh acquisition or quota claim")
    try:
        for number, (agent, query) in enumerate(cases, 1):
            case_id = f"{number:02d}-{agent}"
            route, field = routes[agent]
            payload = {field: query}
            payload["research_profile"] = args.research_profile
            if args.capture_from:
                # Historical replay replaces the old discovery/reader boundaries,
                # not the new raw-harvest engine. Keep this mode network-blocked.
                payload.pop("research_profile")
                from backend.services.research.research_engine import research_engine
                research_engine.budget.research_profile = None
            if agent == "trending":
                payload["category"] = "business" if query == "electric vehicles" else "technology"
            if args.query and args.query[number - 1]:
                payload["query"] = args.query[number - 1]
            if manifest:
                definition = manifest[number - 1]
                payload["query"] = definition["query"]
                if agent == "trending":
                    payload["asset_name"] = query
                    payload["category"] = definition.get("category", "general")
            print("START " + case_id + " " + query, flush=True)
            started = time.perf_counter()
            sampler = ResourceSampler()
            with ExitStack() as stack:
                stack.enter_context(sampler)
                observer = None
                if args.observe_website_http:
                    from scripts.audits.website_yield_observer import WebsiteYieldObserver
                    observer = stack.enter_context(WebsiteYieldObserver())
                if args.capture_from:
                    saved = json.loads((args.capture_from / (case_id + ".json")).read_text(encoding="utf-8"))
                    from backend.services.agent_reach.channels import EvidenceFragment, RetrievalResult, QueryExecutionRecord
                    corpus = saved.get("research_corpus") or {}
                    candidates = {}
                    # Native display records redact page links. Rich captured
                    # corpus metadata must win, not disappear during replay.
                    for record in native_source_records(saved) + corpus.get("raw_candidates", []) + corpus.get("deep_read_sources", []):
                        identity = record.get("id") or record.get("evidence_id")
                        if identity:
                            prior = candidates.get(identity) or {}
                            candidates[identity] = {**prior, **record, "metadata": {**(prior.get("metadata") or {}), **(record.get("metadata") or {})}}
                    fragments = []
                    for identity, record in candidates.items():
                        meta = record.get("metadata") or {}
                        fragments.append(EvidenceFragment(evidence_id=identity,
                            title=record.get("title", ""), content=record.get("content", ""),
                            snippet=record.get("snippet", ""), url=record.get("canonical_url") or record.get("url", ""),
                            author=record.get("author") or record.get("source_name", ""),
                            published=record.get("published_at", ""), channel_name=record.get("channel") or record.get("platform", "web"),
                            platform=record.get("platform") or record.get("channel", "web"),
                            query_id=record.get("query_id") or meta.get("query_id", ""),
                            query_class=record.get("query_class") or meta.get("query_class", "general"),
                            query_text=record.get("query_text") or meta.get("query_text", ""),
                            content_depth=record.get("content_depth") or meta.get("content_depth", "UNKNOWN"),
                            raw_metadata=meta))
                    allowed_fields = {f.name for f in fields(QueryExecutionRecord)}
                    records = [QueryExecutionRecord(**{k:v for k,v in row.items() if k in allowed_fields})
                               for row in corpus.get("queries", [])]
                    retrieval = RetrievalResult(query=query, domain={"scout": "financial", "brandshield": "brand", "personal_watch": "personal", "trending": "trending"}[agent], fragments=fragments, query_records=records)
                    stack.enter_context(patch("backend.application.research.acquisition.BroadDiscoveryStage.run", return_value=retrieval))
                    prior_attempts = list((saved.get("retrieval_trace") or {}).get("acquisition_attempts", []))
                    prior_attempts_exported = False
                    def saved_reads(ranked, max_reads, timeout_per_read):
                        nonlocal prior_attempts_exported
                        # Restore only previously acquired bytes, never search
                        # snippets. Preserve the recorded depth and capture IDs.
                        restored = []
                        for item in ranked:
                            source = candidates.get(item.id) or {}
                            meta = source.get("metadata") or {}
                            if not source.get("content") or not (source.get("read_status") == "SUCCESS" or meta.get("read_success")):
                                continue
                            item.content = source["content"]
                            item.content_depth = source.get("content_depth") or meta.get("content_depth", "UNKNOWN")
                            item.metadata.update(meta)
                            item.read_status = "SUCCESS"
                            item.acquisition_attempt_id = source.get("acquisition_attempt_id") or item.acquisition_attempt_id
                            item.acquired_id = source.get("acquired_id") or source.get("acquired_candidate_id") or item.acquired_id
                            restored.append(item)
                            if len(restored) >= max_reads:
                                break
                        # Preserve prior failures as saved observations exactly
                        # once. These counters are NOT fresh network attempts.
                        observed = [] if prior_attempts_exported else [
                            {**row, "observation_origin": "SAVED_CAPTURE"} for row in prior_attempts]
                        prior_attempts_exported = True
                        return restored, {"attempted": len(observed), "successful": sum(row.get("status") == "SUCCESS" for row in observed),
                                          "failed": sum(row.get("status") != "SUCCESS" for row in observed), "cached": len(restored),
                                          "acquisition_attempts": observed,
                                          "total_chars_read": 0, "read_urls": [], "mode": "SAVED_ACQUISITION_RESTORED_NO_HTTP"}
                    stack.enter_context(patch("backend.services.research.deep_reader.deep_reader.deep_read", side_effect=saved_reads))
                    stack.enter_context(patch("backend.services.agent_reach.agent_reach_service.search_channel", return_value=[]))
                    stack.enter_context(patch("backend.services.research.primary_source_escalator.primary_source_escalator.escalate", return_value=([], {"queries": [], "escalations": 0})))
                response = client.post("/api/" + route + "/stream", json=payload)
            # Preserve the exact sanitized response before parsing/exporting
            # nested provider metadata. This is not another network request.
            (out / (case_id + "-response.sse")).write_text(redact(response.text), encoding="utf-8")
            if observer is not None:
                save(case_id + "-http.json", observer.export())
                save(case_id + "-observed-pools.json", observer.captured_pools())
            events = parse_events(response.text)
            native = next((event["data"]["result"] for event in events if event["event"] == "result"), {})
            save(case_id + "-events.json", events)
            save(case_id + ".json", native)
            save(case_id + "-pipeline.json", {"mode": summary["mode"], "live_ai_generation_requests": 0 if not args.allow_live_ai else None,
                "research_corpus": native.get("research_corpus"), "evidence": native.get("sources") or native.get("evidence"),
                "findings": native.get("findings_structured") or native.get("findings"),
                "api_and_frontend_report": native.get("unified_report"),
                "limitations": "Retained provider text only, not uncaptured HTML or inferred missing evidence. Saved-mode reads are not fresh observations."})
            records = native_source_records(native)
            texts = [str(e.get("content") or e.get("snippet") or "") for e in records if isinstance(e, dict)]
            report = native.get("unified_report") or {}
            row = {"case_id": case_id, "agent": agent, "input": query, "http_status": response.status_code,
                   "seconds": round(time.perf_counter() - started, 2), "result_event": bool(native),
                   "error_events": [e["data"] for e in events if e["event"] == "error"],
                   "records": len(records), "words": sum(len(t.split()) for t in texts),
                   "kb": round(sum(len(t.encode("utf-8")) for t in texts) / 1000, 3),
                   "findings": report.get("findings", []), "summary": report.get("summary"),
                   "source_titles": [e.get("title") for e in records],
                   "background_evidence_ids": native.get("background_evidence_ids", []),
                   "resource_usage": sampler.result()}
            if manifest:
                row.update(prompt_id=definition["id"], requested_prompt=definition["query"],
                           effective_payload=payload, application_sha256=initial)
            summary["cases"].append(row)
            print(redact(json.dumps(row, ensure_ascii=True)), flush=True)
            save("summary.json", summary)
    finally:
        client.close()
        summary["final_application_sha256"] = fingerprint()
        summary["stable_application"] = initial == summary["final_application_sha256"]
        summary["live_ai_calls_reserved"] = max(0, call_count() - initial_ai_count)
        summary["shared_ai_calls_reserved_before_batch"] = initial_ai_count
        summary["shared_ai_calls_reserved_after_batch"] = call_count()
        summary["live_ai_observations"] = observations()
        save("summary.json", summary)
        run_stack.close()
    return int(not summary["stable_application"] or any(not r["result_event"] or r["error_events"] for r in summary["cases"]))


if __name__ == "__main__":
    raise SystemExit(main())
