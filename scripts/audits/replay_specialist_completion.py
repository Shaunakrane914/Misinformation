"""Replay genuine captured sources through current four-agent API and SSE.

Only the acquisition boundary is replaced: original source IDs, URLs, titles,
dates and hash-validated retained text enter the current qualification, synthesis,
specialist and shared-report code. This is not new live autonomous discovery.
Fresh local progress events describe offline processing, not provider searches.
"""
from __future__ import annotations

import argparse
import copy
from contextlib import ExitStack
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import sys
from dataclasses import fields
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]


def saved_harvest(payload):
    from scripts.audits.requalify_raw_pool import locate_pool
    from backend.services.research.raw_pool import RawAcquisitionPool
    from backend.services.research.harvesting import HarvestResult
    from backend.services.research.research_models import EvidenceItem
    from backend.services.agent_reach.channels import QueryExecutionRecord

    original = locate_pool(payload)
    pool = RawAcquisitionPool.from_export(original)
    captures = pool.to_evidence_items()
    # The raw pool stores bodies/identities, but not every native acquisition
    # lineage ID. Restore only IDs actually recorded for this exact ID/URL/body
    # tuple, so an acquired-body gate is exercised rather than bypassed or given
    # invented success identifiers. Other pool-only captures remain unknown.
    native_captures = (payload.get("research_corpus") or {}).get("deep_read_sources", [])
    for capture in captures:
        digest = hashlib.sha256(capture.content.encode("utf-8")).hexdigest()
        matches = [row for row in native_captures if isinstance(row, dict)
            and (row.get("id") or row.get("evidence_id")) == capture.id
            and (row.get("canonical_url") or row.get("url")) == capture.canonical_url
            and hashlib.sha256(str(row.get("content") or "").encode("utf-8")).hexdigest() == digest]
        if len(matches) == 1:
            for name in ("acquired_id", "acquisition_attempt_id", "discovered_id", "ranked_id", "accepted_id"):
                value = matches[0].get(name)
                if isinstance(value, str) and value:
                    setattr(capture, name, value)
    captures_by_id = {item.id: item for item in captures}
    original_candidates = {row.get("id") or row.get("evidence_id"): row
        for row in (payload.get("research_corpus") or {}).get("raw_candidates", []) if isinstance(row, dict)}
    candidates = []
    for source in original["sources"]:
        item = copy.deepcopy(captures_by_id.get(source["source_id"]))
        if item is None:
            item = EvidenceItem(id=source["source_id"], canonical_url=source["source_url"],
                title=source["title"], snippet=source["discovery_snippet"], query_id=source["query_id"],
                source_name=source["publisher"], source_domain=source["publisher_host"],
                published_at=source["published_at"] or "", content_depth=source.get("content_depth") or "SNIPPET")
        # The pool does not record every original channel/class. Unknown remains
        # unknown, never an invented query lifecycle or source-role assignment.
        item.metadata["replay_original_source_type"] = source["source_type"]
        original_candidate = original_candidates.get(source["source_id"]) or {}
        original_metadata = original_candidate.get("metadata") or {}
        if type(original_metadata.get("harvest_acquisition_eligible")) is bool:
            item.metadata["harvest_acquisition_eligible"] = original_metadata["harvest_acquisition_eligible"]
        candidates.append(item)
    trace = payload.get("deep_research_trace") or payload.get("retrieval_trace") or {}
    attempts = copy.deepcopy(trace.get("acquisition_attempts") or [])
    # Preserve saved read failures/admissions as historical observations rather
    # than replacing them with one invented success per restored capture.
    for attempt in attempts:
        attempt["observation_origin"] = "SAVED_CAPTURE_NOT_REEXECUTED"
    metrics = trace.get("acquisition_metrics") or {}
    allowed_fields = {field.name for field in fields(QueryExecutionRecord)}
    records = (payload.get("research_corpus") or {}).get("queries") or trace.get("query_records") or []
    records = [QueryExecutionRecord(**{key: value for key, value in row.items() if key in allowed_fields})
               for row in records if isinstance(row, dict)]
    return HarvestResult(candidates=candidates, captures=captures, query_records=records,
        metrics={"mode": "SAVED_NATIVE_SOURCE_REPLAY", "halt_reason": "SAVED_CAPTURE_SET_EXHAUSTED",
                 "candidate_urls_discovered": len(candidates), "new_discovery_queries": 0,
                 "new_network_calls": 0, "original_discovery_replayed_not_reexecuted": True},
        read_telemetry={"attempted": metrics.get("reads_attempted", len(attempts) or len(captures)), "successful": len(captures),
            "failed": sum(attempt.get("status") != "SUCCESS" for attempt in attempts),
            "total_chars_read": sum(len(item.content) for item in captures),
            "mode": "SAVED_ACQUISITION_OBSERVATIONS_NOT_FRESH_READS",
            "acquisition_attempts": attempts})


def replay(payload, agent, subject, *, reference_time=None, category=None):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from backend.api.agents import router
    from backend.agents.scout.agent import ScoutAgent
    from backend.infrastructure.llm.gateway import DefaultLLMGateway
    from backend.services.research.relevance_gate import RelevanceGate

    harvested = saved_harvest(payload)
    app = FastAPI()
    app.include_router(router)
    endpoint, field = {"scout": ("scout/analyze", "ticker"), "personal_watch": ("personal/scan", "name"),
        "brandshield": ("brandshield/scan", "brand_name"), "trending": ("trending/scan", "query")}[agent]
    path = "/api/" + endpoint + "/stream"
    request = {field: subject, "research_profile": "DEEP"}
    if agent == "trending":
        request["category"] = category or "technology"
    # Existing quote bytes or honest absence are replayed; no new quote lookup.
    with ExitStack() as stack:
        stack.enter_context(patch("backend.services.research.harvesting.HarvestingEngine.run", side_effect=lambda **_: copy.deepcopy(harvested)))
        stack.enter_context(patch.object(ScoutAgent, "check_stock_impact", return_value=copy.deepcopy(payload.get("stock") or {})))
        generation_guard = stack.enter_context(patch.object(DefaultLLMGateway, "generate_text",
            side_effect=RuntimeError("All real and synthetic generation forbidden in source replay")))
        if reference_time is not None:
            gate = RelevanceGate(reference_time=reference_time)
            stack.enter_context(patch("backend.application.research.harvest_pipeline.relevance_gate", gate))
            stack.enter_context(patch("backend.services.research.relevance_gate.relevance_gate", gate))
            # Trending imports the singleton at module load. Keep its second
            # body gate on the same saved observation clock, not today's clock.
            stack.enter_context(patch("backend.agents.trending.agent.relevance_gate", gate))
        response = TestClient(app).post(path, json=request)
    if generation_guard.call_count:
        raise RuntimeError("Replay attempted generation; no zero-AI acceptance is claimed")
    events = []
    for part in response.text.replace("\r\n", "\n").split("\n\n"):
        lines = part.splitlines()
        kind = next((line[7:] for line in lines if line.startswith("event: ")), None)
        data = "\n".join(line[6:] for line in lines if line.startswith("data: "))
        if kind and data:
            events.append({"event": kind, "data": json.loads(data)})
    results = [event["data"]["result"] for event in events if event["event"] == "result"]
    if response.status_code != 200 or len(results) != 1 or any(event["event"] == "error" for event in events):
        raise RuntimeError("Current API/SSE did not return exactly one complete result")
    return results[0], events


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--agent", choices=("scout", "personal_watch", "brandshield", "trending"), required=True)
    parser.add_argument("--subject", required=True)
    parser.add_argument("--reference-time", help="Timezone-aware original observation time; defaults to saved pool created_at, never advances old source dates")
    parser.add_argument("--category", help="Trending category used by the original normal query; default technology")
    args = parser.parse_args(argv)
    if args.input.is_symlink() or not args.input.is_file() or args.input.stat().st_size > 80_000_000:
        raise ValueError("Supply a bounded regular native-response file")
    protected = [ROOT / directory for directory in ("backend/data/dossiers", "artifacts", "research", "tests/retrieval_benchmark")]
    output = args.output_dir.resolve()
    if output.exists() or any(output == path.resolve() or output.is_relative_to(path.resolve()) for path in protected):
        raise ValueError("Output must be a fresh directory outside protected evidence trees")
    output.mkdir(parents=True, exist_ok=False)
    encoded = args.input.read_bytes()
    payload = json.loads(encoded)
    sys.path.insert(0, str(ROOT))
    from scripts.validation.isolated_runtime import block_live_network, isolated_environment
    block_live_network()
    environment = isolated_environment(output / "runtime")
    environment.update(AEGIS_MOCK_LLM="false", AEGIS_SEARCH_ADVISOR_ENABLED="false",
                       AEGIS_EVIDENCE_ADVISOR_ENABLED="false", AEGIS_RAW_POOL_PERSIST="false")
    os.environ.update(environment)
    from scripts.audits.requalify_raw_pool import locate_pool
    original_pool = locate_pool(payload)
    reference_value = args.reference_time or original_pool.get("created_at")
    reference = datetime.fromisoformat(reference_value.replace("Z", "+00:00")) if reference_value else None
    if reference is not None and reference.tzinfo is None:
        raise ValueError("Reference time must include timezone")
    if args.agent == "trending" and reference is None:
        raise ValueError("Trending replay needs an original timezone-aware observation time")
    result, events = replay(payload, args.agent, args.subject, reference_time=reference, category=args.category)
    raw = result.get("research_corpus", {}).get("raw_acquisition_pool", {})
    originals = {source["source_id"]: source for source in original_pool["sources"]}
    unchanged = all(source["source_id"] in originals and all(source.get(key) == originals[source["source_id"]].get(key)
        for key in ("source_url", "title", "raw_content_hash", "readable_text")) for source in raw.get("sources", []))
    if len(raw.get("sources", [])) != len(originals) or not unchanged:
        raise RuntimeError("Replay changed/lost an original raw source identity or capture")
    publication_changes = [{"source_id": source["source_id"], "original": originals[source["source_id"]].get("published_at"),
        "current": source.get("published_at"), "current_basis": source.get("publication_time_basis")}
        for source in raw.get("sources", []) if source.get("published_at") != originals[source["source_id"]].get("published_at")]
    prefix = {"scout": "01-scout", "personal_watch": "02-personal_watch",
              "brandshield": "03-brandshield", "trending": "04-trending"}[args.agent]
    report = {"mode": "OFFLINE_GENUINE_SOURCE_TO_API_SSE_REPLAY", "agent": args.agent, "subject": args.subject,
        "input_sha256": hashlib.sha256(encoded).hexdigest(), "new_network_calls": 0, "model_calls": 0,
        "acquisition_boundary": "HASH_VALIDATED_SAVED_SOURCES; LIVE_DISCOVERY_NOT_RERUN",
        "api_transport": "CURRENT_AGENT_ROUTER_IN_ISOLATED_ASGI_APP; NO_BACKGROUND_LIFESPAN",
        "unchanged_source_id_url_title_body_hash": unchanged,
        "unchanged_source_id_url_title_date_body_hash": unchanged and not publication_changes,
        "publication_changes": publication_changes,
        "temporal_reference": reference.isoformat() if reference else None,
        "original_raw_sources": len(originals),
        "processing_progress_events": sum(event["event"] == "progress" for event in events),
        "acquisition_metrics": result.get("deep_research_trace", {}).get("acquisition_metrics", {}),
        "public_statements": result.get("public_statements", []),
        "identity_risk": result.get("identity_risk"), "filing_comparison": result.get("filing_comparison"),
        "generation_policy": "LIVE_AND_SYNTHETIC_GATEWAY_GENERATION_BLOCKED; ZERO_ATTEMPTS_REQUIRED",
        "qualified_sources": [{"source_id": source["source_id"], "source_url": source["source_url"],
            "raw_content_hash": source["raw_content_hash"], "retained_words": source["word_count"],
            "qualification_status": source["qualification_status"], "useful_words": source["useful_words"]}
            for source in raw.get("sources", []) if source["qualification_status"] == "QUALIFIED"],
        "limitations": ["Source replay proves current interpretation/projection, not new live provider health or recall.",
            "Fresh processing SSE events are not original network progress or latency measurements."]}
    for name, value in ((prefix + ".json", result), (prefix + "-events.json", events), ("manifest.json", report)):
        with (output / name).open("x", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
    print(json.dumps({"mode": report["mode"], "agent": args.agent, "output_dir": str(output),
        "source_identity_preserved": unchanged, "progress_events": report["processing_progress_events"],
        "model_calls": 0, "new_network_calls": 0}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
