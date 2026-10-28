"""Strict, network-blocked requalification of a saved raw acquisition pool.

No acquisition, AI, verdict generation, dossier writes, or edits to source
captures. Accepts a standalone pool or its full-text copy embedded in an agent
response. Output is a new file, never an overwrite of old audit evidence.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
import sys
import tempfile


REPO_ROOT = Path(__file__).resolve().parents[2]
MAX_INPUT_BYTES = 80_000_000  # Envelopes may contain duplicated bounded pools.
MODE = "OFFLINE_RAW_REQUALIFICATION"
ELIGIBLE_TYPES = {"ARTICLE_BODY", "OFFICIAL_DOCUMENT", "COMMUNITY_POST", "STRUCTURED_PUBLIC_DATA"}


def locate_pool(payload):
    """Only documented envelope locations, not arbitrary recursive field search."""
    if not isinstance(payload, dict):
        raise ValueError("Input must be a raw pool or JSON response object")
    roots = [payload]
    for key in ("result", "data"):
        if isinstance(payload.get(key), dict):
            roots.append(payload[key])
            if isinstance(payload[key].get("result"), dict):
                roots.append(payload[key]["result"])
    candidates = []
    for root in roots:
        if root.get("schema_version") == "raw-acquisition-pool-v1":
            candidates.append(root)
        candidates.append(root.get("raw_acquisition_pool"))
        for key in ("research_corpus", "deep_research_trace", "retrieval_trace"):
            section = root.get(key)
            if isinstance(section, dict):
                candidates.append(section.get("raw_acquisition_pool"))
    textless = False
    for pool in candidates:
        if not isinstance(pool, dict) or pool.get("schema_version") != "raw-acquisition-pool-v1":
            continue
        sources = pool.get("sources")
        if isinstance(sources, list) and any(isinstance(source, dict) and "readable_text" not in source for source in sources):
            textless = True
            continue
        return pool
    if textless:
        raise ValueError("TEXTLESS_POOL_NOT_REPROCESSABLE: supply the original full-text raw pool, not the trace projection")
    raise ValueError("No full raw acquisition pool found in the documented response locations")


def requalify_payload(payload, *, target, domain, intent="", reference_time=None, disambiguate_aliases=False):
    """Deterministic filtering only; CLI isolates before these application imports.

    Returned source snapshots are the original input pool, not rewritten bodies.
    Requalification decisions and exact offsets live in a separate projection.
    This helper performs no network, model, notification or persistence calls.
    """
    from backend.services.research.body_context import reconcile_captured_context
    from backend.services.research.passage_extractor import PassageExtractor, has_usable_passage
    from backend.services.research.raw_pool import RawAcquisitionPool
    from backend.services.research.relevance_gate import RelevanceGate
    from backend.services.research.source_quality import source_quality_engine

    original = locate_pool(payload)
    original_digest = hashlib.sha256(json.dumps(original, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    pool = RawAcquisitionPool.from_export(original, allow_ambiguous_aliases=disambiguate_aliases)
    captured = {item.id: item for item in pool.to_evidence_items()}
    gate = RelevanceGate(reference_time=reference_time)
    extractor = PassageExtractor()
    decisions = []
    for record in pool.export()["sources"]:
        source_id = record["source_id"]
        item = captured.get(source_id)
        row = {"source_id": source_id, "source_url": record["source_url"], "source_type": record["source_type"],
            "raw_content_hash": record["raw_content_hash"], "captured_words": record["word_count"],
            "qualification_status": "REJECTED", "reasons": [], "passage": None}
        if item is None:
            row["reasons"] = ["NO_ACQUIRED_SOURCE_TEXT"]
        elif record["duplicate_of"]:
            row["qualification_status"] = "DUPLICATE"
            row["reasons"] = ["EXACT_CAPTURE_DUPLICATE"]
            row["duplicate_of"] = record["duplicate_of"]
        else:
            item.metadata["temporal_required"] = domain == "trending"
            reconcile_captured_context(item)
            # The gate must assess actual body context, not the retained search
            # snippet. This mutation affects the reconstructed copy only.
            item.snippet = item.content[:12_000]
            item.relevant_excerpt = ""
            source_quality_engine.classify_and_score(item, target_name=target)
            assessment = gate.evaluate_item(item, target, domain=domain, intent=intent, provisional_read=False)
            row["relevance_assessment"] = assessment.to_dict()
            row["observed_published_at"] = item.published_at or None
            structural = record["source_type"] in ELIGIBLE_TYPES
            page = item.metadata.get("page_metadata") or {}
            if record["source_type"] == "ARTICLE_BODY":
                # Recheck the observed extraction marker: importing a stored
                # label must not upgrade an unclassified page into an article.
                structural = (page.get("body_kind") == "ARTICLE_BODY"
                    or (page.get("body_quality") or {}).get("body_kind") == "ARTICLE_BODY")
            eligible = structural and assessment.is_accepted
            item.metadata["layer2_eligible"] = eligible
            item.metadata["temporal_required"] = domain == "trending"
            item.metadata["temporal_eligible"] = assessment.is_accepted if domain == "trending" else True
            if not structural:
                row["reasons"] = ["NO_ELIGIBLE_STRUCTURAL_BODY"]
            elif not assessment.is_accepted:
                row["reasons"] = [assessment.rejection_reason or "BODY_NOT_RELEVANT"]
            else:
                extractor.extract_passages([item], target, intent=intent, domain=domain)
                exact = (0 <= item.excerpt_start < item.excerpt_end <= len(item.content)
                         and item.content[item.excerpt_start:item.excerpt_end] == item.relevant_excerpt)
                if item.extraction_status == "SUCCESS" and item.relevant_excerpt and exact and has_usable_passage(item):
                    row["qualification_status"] = "QUALIFIED"
                    row["passage"] = {"text": item.relevant_excerpt, "start": item.excerpt_start,
                        "end": item.excerpt_end, "word_count": len(item.relevant_excerpt.split()),
                        "source_id": source_id, "claim_support": "NOT_ADJUDICATED"}
                    # Every bounded paragraph that passed the same gates (additive; the winner above is unchanged).
                    row["workbench_passages"] = [
                        {"text": p["text"], "start": p["start"], "end": p["end"], "word_count": len(p["text"].split())}
                        for p in (item.metadata.get("evidence_passages") or [])
                        if isinstance(p, dict) and isinstance(p.get("text"), str)
                        and item.content[p.get("start", -1):p.get("end", -1)] == p["text"]]
                else:
                    row["reasons"] = [item.extraction_status if exact else "NO_EXACT_USABLE_PASSAGE"]
        pool.mark_qualification(source_id, row["qualification_status"], row["reasons"],
            useful_words=row["passage"]["word_count"] if row["passage"] else 0)
        decisions.append(row)
    return {
        "mode": MODE, "generated_at": datetime.now(timezone.utc).isoformat(),
        "network_policy": "NO_NETWORK_CALL_PATHS", "ai_generation": "DISABLED",
        "fresh_network_calls": 0, "model_calls": 0, "new_source_acquisition": False,
        "request": {"target": target, "domain": domain, "intent": intent,
            "reference_time": reference_time.isoformat() if reference_time else "CURRENT_UTC_AT_REQUALIFICATION"},
        "original_pool_sha256": original_digest, "raw_acquisition_pool": original,
        "alias_disambiguation": {"enabled": bool(disambiguate_aliases),
            "ambiguous_aliases": pool.export().get("ambiguous_aliases", []),
            "prior_citations_repaired": False,
            "policy": "UNIQUE_RAW_SOURCE_IDS_ONLY; AMBIGUOUS_NATIVE_ALIAS_LOOKUPS_DISABLED"},
        "requalification": {"stats": pool.stats(), "decisions": decisions,
            "source_projection": pool.export(include_text=False)["sources"]},
        "limitations": ["Saved source replay does not establish live autonomous discovery.",
            "A qualified passage is not a verified finding or adjudicated claim.",
            "Publisher grouping does not establish source independence.",
            "Explicit alias disambiguation excludes ambiguous joins; it does not repair prior citations or verdicts.",
            "No investigation report, verdict, dossier or frontend acceptance was generated."],
    }


def _safe_output_path(path):
    resolved = path.resolve()
    protected = (REPO_ROOT / "backend" / "data" / "dossiers", REPO_ROOT / "artifacts",
                 REPO_ROOT / "research", REPO_ROOT / "tests" / "retrieval_benchmark")
    if any(resolved == root.resolve() or resolved.is_relative_to(root.resolve()) for root in protected):
        raise ValueError("Output must not target protected historical or benchmark trees")
    if path.exists() or path.is_symlink():
        raise FileExistsError("Output exists; choose a fresh filename")
    return resolved


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--target", required=True)
    parser.add_argument("--domain", choices=("financial", "trending", "brand", "personal", "general"), required=True)
    parser.add_argument("--intent", default="")
    parser.add_argument("--reference-time", help="ISO8601 timezone-aware reference for repeatable temporal checks")
    parser.add_argument("--disambiguate-aliases", action="store_true",
        help="Explicit offline rescue: exclude ambiguous native aliases from lookup; preserve originals and validate unique raw IDs/URLs/hashes")
    args = parser.parse_args(argv)
    try:
        if not args.target.strip() or len(args.target) > 5000 or len(args.intent) > 5000:
            raise ValueError("Provide a bounded nonempty target and optional intent")
        output = _safe_output_path(args.output)
        if args.input.is_symlink() or not args.input.is_file() or args.input.stat().st_size > MAX_INPUT_BYTES:
            raise ValueError("Input must be a bounded regular JSON file (at most 80MB)")
        with args.input.open("rb") as stream:
            encoded = stream.read(MAX_INPUT_BYTES + 1)
        if len(encoded) > MAX_INPUT_BYTES:
            raise ValueError("Input exceeds the bounded file limit")
        reference = datetime.fromisoformat(args.reference_time.replace("Z", "+00:00")) if args.reference_time else None
        if reference is not None and reference.tzinfo is None:
            raise ValueError("Reference time must include a timezone")
        sys.path.insert(0, str(REPO_ROOT))
        # Before application imports: deny provider transports and subprocesses,
        # isolate storage and blank secrets so dotenv cannot restore credentials.
        from scripts.validation.isolated_runtime import block_live_network, isolated_environment
        from dotenv import dotenv_values
        block_live_network()
        with tempfile.TemporaryDirectory(prefix="aegis-offline-requalification-") as directory:
            environment = isolated_environment(Path(directory))
            for name in set(environment) | set(dotenv_values(REPO_ROOT / ".env")):
                if any(marker in name.upper() for marker in ("API_KEY", "TOKEN", "SECRET", "PASSWORD", "COOKIE")):
                    environment[name] = ""
            environment.update(AEGIS_MOCK_LLM="false", AEGIS_SEARCH_ADVISOR_ENABLED="false",
                AEGIS_EVIDENCE_ADVISOR_ENABLED="false", AEGIS_AI_POLICY_DB=str(Path(directory) / "ai-disabled.db"))
            os.environ.update(environment)
            result = requalify_payload(json.loads(encoded), target=args.target.strip(), domain=args.domain,
                intent=args.intent, reference_time=reference, disambiguate_aliases=args.disambiguate_aliases)
        result["input_sha256"] = hashlib.sha256(encoded).hexdigest()
        result["input_bytes"] = len(encoded)
        result["network_policy"] = "LIVE_NETWORK_BLOCKED_BEFORE_APPLICATION_IMPORTS"
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("x", encoding="utf-8") as stream:
            json.dump(result, stream, ensure_ascii=False, indent=2)
        print(json.dumps({"mode": MODE, "output": str(output), "stats": result["requalification"]["stats"],
            "fresh_network_calls": 0, "model_calls": 0}))
        return 0
    except (OSError, ValueError, KeyError, TypeError) as error:
        # Do not echo input source bodies, credential values or HTTP responses.
        reason = str(error)
        safe_prefixes = ("TEXTLESS_POOL_NOT_REPROCESSABLE", "Output ", "Reference time ",
            "Input ", "Provide a bounded", "No full raw acquisition pool", "Capture hash mismatch",
            "Raw capture hash mismatch", "Source counts do not match", "Unsupported raw pool schema")
        reason = reason[:300] if reason.startswith(safe_prefixes) else "Invalid saved source pool or unsafe output; no input content emitted"
        print(json.dumps({"mode": MODE, "status": "FAILED", "error_type": type(error).__name__,
            "reason": reason}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
