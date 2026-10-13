"""
Aegis Protocol — Claims & Truth Verification Router
====================================================
Manages synchronous Truth Dossier generation, asynchronous background claim ingestion,
and status/evidence retrieval.

Endpoints
---------
POST /api/claims/verify       — Synchronous multi-agent fact-check (returns full Truth Dossier).
POST /api/claims/submit       — Async claim ingestion; queues a background investigation.
POST /api/ingest              — Alias for /api/claims/submit.
POST /api/submit              — Alias for /api/claims/submit.
GET  /api/claims/{id}         — Retrieve claim status and verdict by ID.
GET  /api/claims/{id}/research — Full forensic research corpus for a claim.
GET  /api/claims/{id}/evidence — All evidence records linked to a claim.
GET  /api/claims             — Paginated list of all known claims.

Design Decisions
----------------
- quality_tensor is NEVER synthesised with hardcoded values; it is None when no genuine
  research corpus was produced, and quality_status reflects this as UNAVAILABLE_NO_CORPUS.
- narrative_forensics (Mandelbrot R², Hawkes R₀, Shannon entropy) are computed only when
  the claim text has ≥10 tokens; fields are None otherwise (no fake defaults).
- Source lineage DAG is always constructed from actual evidence candidates — never from
  placeholder nodes.
"""

import time
import math
import re
import json
import hashlib
import logging
import urllib.parse
from collections import Counter
from datetime import datetime
from typing import Any, Dict, List, Optional

try:
    import numpy as np
except ImportError:
    np = None

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field, model_validator

from backend.db import database as db
from backend.workers.claim_worker import process_claim
from backend.services.research.source_lineage import SourceLineageEngine
from backend.services.research.replay_ledger import replay_ledger
from backend.services.research.research_models import EvidenceItem, SourceRole, SourceTier
from backend.services.report_builder import ReportBuilder

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Claims & Verification"])

# Lazy agent getters
_claim_ingestion_agent = None
_research_agent = None
_investigator_agent = None


def get_claim_ingestion_agent():
    global _claim_ingestion_agent
    if _claim_ingestion_agent is None:
        from backend.agents.claim_ingestion_agent import ClaimIngestionAgent
        _claim_ingestion_agent = ClaimIngestionAgent()
    return _claim_ingestion_agent


def get_research_agent():
    global _research_agent
    if _research_agent is None:
        from backend.agents.research_agent import ResearchAgent
        _research_agent = ResearchAgent()
    return _research_agent


def get_investigator_agent():
    global _investigator_agent
    if _investigator_agent is None:
        from backend.agents.investigator_agent import InvestigatorAgent
        _investigator_agent = InvestigatorAgent()
    return _investigator_agent


# ── Request / Response Models ────────────────────────────────────────────────

class ClaimVerifyRequest(BaseModel):
    claim_text: Optional[str] = Field(
        None,
        description="The statement, news headline, or rumor to fact-check with multi-agent intelligence.",
        json_schema_extra={"example": "Scientists discovered that drinking boiled lemon water completely cures cancer within 48 hours."}
    )
    claim: Optional[str] = Field(None, description="Alias for claim_text.")
    source_url: Optional[str] = Field(
        None,
        description="Optional source link or tweet URL where the claim was observed.",
        json_schema_extra={"example": "https://twitter.com/health_news/status/18361234567"}
    )

    @model_validator(mode="before")
    @classmethod
    def resolve_claim_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            text = data.get("claim_text") or data.get("claim")
            if not text or not str(text).strip() or len(str(text).strip()) < 5:
                raise ValueError("A valid claim or claim_text of at least 5 characters is required.")
            data["claim_text"] = str(text).strip()
        return data


class ClaimSubmitRequest(BaseModel):
    claim_text: Optional[str] = Field(
        None,
        description="Claim text for background queuing and database insertion.",
        json_schema_extra={"example": "Leaked memo reveals Nvidia is acquiring AMD in $150B secret merger."}
    )
    claim: Optional[str] = Field(None, description="Alias for claim_text.")
    source_url: Optional[str] = Field(
        None,
        description="Optional origin URL.",
        json_schema_extra={"example": "https://reddit.com/r/stocks/comments/xyz123"}
    )

    @model_validator(mode="before")
    @classmethod
    def resolve_claim_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            text = data.get("claim_text") or data.get("claim")
            if not text or not str(text).strip() or len(str(text).strip()) < 5:
                raise ValueError("A valid claim or claim_text of at least 5 characters is required.")
            data["claim_text"] = str(text).strip()
        return data


class ClaimSubmitResponse(BaseModel):
    claim_id: str
    status: str
    is_new: bool


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.post(
    "/api/claims/verify",
    summary="Direct Synchronous Multi-Agent Fact-Check (Truth Dossier)"
)
def verify_claim_sync(request: ClaimVerifyRequest):
    """
    Execute an immediate, end-to-end multi-agent verification pass on a claim.
    Returns the complete 5-section Truth Dossier synchronously.
    """
    start_time = time.perf_counter()
    claim_raw = request.claim_text.strip()
    logger.info(f"[API] POST /api/claims/verify - Claim: {claim_raw[:60]}...")

    if not claim_raw:
        raise HTTPException(status_code=400, detail="Claim text cannot be empty.")

    try:
        # 1. Normalization & Atomic Claim Decomposition via ClaimIngestionAgent
        claim_ingestion = get_claim_ingestion_agent()
        ingest_res = claim_ingestion.ingest(claim_text=claim_raw, source_url=request.source_url)
        norm_text = ingest_res.get("normalized_text") or claim_raw
        claim_hash = ingest_res.get("claim_id") or hashlib.sha256(norm_text.encode('utf-8')).hexdigest()
        atomic_claims = claim_ingestion.decompose_claim(norm_text)

        # 2. Gather Evidence via ResearchAgent using shared ResearchEngine
        research_agent = get_research_agent()
        evidence_json = {}
        try:
            evidence_json = research_agent.gather_evidence_structured(norm_text, source_url=request.source_url)
        except Exception as e_ev:
            logger.warning(f"[VerifySync] Research structured evidence note: {e_ev}")
            try:
                evidence_str = research_agent.gather_evidence(norm_text, source_url=request.source_url)
                if isinstance(evidence_str, str):
                    cleaned_ev = evidence_str.strip()
                    if cleaned_ev.startswith("```json"):
                        cleaned_ev = cleaned_ev.split("```json")[1].split("```")[0].strip()
                    elif cleaned_ev.startswith("```"):
                        cleaned_ev = cleaned_ev.split("```")[1].split("```")[0].strip()
                    evidence_json = json.loads(cleaned_ev)
                elif isinstance(evidence_str, dict):
                    evidence_json = evidence_str
            except Exception as e_ev2:
                logger.warning(f"[VerifySync] Fallback evidence note: {e_ev2}")
                evidence_json = {"supporting_evidence": [], "refuting_evidence": [], "overall_evidence_confidence": 0.0}
        if not isinstance(evidence_json, dict):
            evidence_json = {"supporting_evidence": [], "refuting_evidence": [], "overall_evidence_confidence": 0.0}

        # 3. Investigate & Stance Reason via InvestigatorAgent
        investigator_agent = get_investigator_agent()
        try:
            investigation_res = investigator_agent.process(norm_text, evidence_json)
            if isinstance(investigation_res, str):
                investigation_res = investigator_agent.extract_verdict(investigation_res)
        except Exception as e_inv:
            logger.warning(f"[VerifySync] Investigation note: {e_inv}")
            try:
                investigation_res = investigator_agent.investigate(norm_text, evidence_json)
                if isinstance(investigation_res, str):
                    investigation_res = investigator_agent.extract_verdict(investigation_res)
            except Exception as e_inv2:
                investigation_res = {
                    "verdict": "Unverified",
                    "confidence": None,
                    "reasoning": "Investigation incomplete due to downstream processing error.",
                    "severity": "Low"
                }

        if isinstance(investigation_res, str):
            investigation_res = investigator_agent.extract_verdict(investigation_res)

        # 4. Multi-channel Social Radar derived from Research Engine & Native Router
        rc = evidence_json.get("research_corpus") or {}
        social_srcs = rc.get("social_sources", [])
        reddit_items = [s for s in social_srcs if s.get("channel") == "reddit" or "reddit.com" in s.get("canonical_url", "")]
        twitter_items = [s for s in social_srcs if s.get("channel") in ("twitter", "x") or "twitter.com" in s.get("canonical_url", "")]
        youtube_items = [s for s in rc.get("video_sources", []) if s.get("channel") == "youtube" or "youtube.com" in s.get("canonical_url", "")]
        news_items = [s for s in rc.get("primary_sources", []) + rc.get("deep_read_sources", []) if s.get("channel") in ("news", "rss")]

        # If social items weren't part of primary corpus, route non-blocking query via NativeRouter
        if not (reddit_items or twitter_items or youtube_items):
            try:
                from backend.services.agent_reach_service import agent_reach_service
                radar_res = agent_reach_service.retrieve_many(
                    channel_queries={"news": [{"query_text": norm_text}], "web": [{"query_text": norm_text}]},
                    domain="fact_check",
                    budget={"max_queries_per_channel": 1, "max_results_per_query": 3, "max_total_evidence": 6},
                    perform_reads=False,
                    timeout=4.0
                )
                for f in radar_res.fragments:
                    news_items.append({"title": f.title, "url": f.url, "source": f.author or f.platform})
            except Exception as e_radar:
                logger.debug(f"[VerifySync] Radar fallback notice: {e_radar}")

        # 5. Narrative Forensics: Empirical Lexical Entropy (No synthetic defaults)
        tokens = re.findall(r"\b[a-zA-Z]{2,}\b", norm_text.lower())
        mandel_r2 = None
        entropy = None
        if len(tokens) >= 10:
            counts = Counter(tokens)
            total_t = len(tokens)
            entropy = round(-sum((c / total_t) * math.log2(c / total_t) for c in counts.values()), 2)
            if np is not None and len(counts) >= 5:
                ranks = np.arange(1, len(counts) + 1)
                freqs = np.array(sorted(counts.values(), reverse=True))
                if freqs[0] > freqs[-1]:
                    corr = np.corrcoef(np.log(ranks), np.log(freqs))[0, 1]
                    mandel_r2 = round(float(corr ** 2), 2) if not np.isnan(corr) else None
                else:
                    mandel_r2 = None

        verdict_str = str(investigation_res.get("verdict", "Unverified")).strip().upper().replace(" ", "_")
        clean_verdict = {
            "TRUE": "TRUE", "SUPPORTED": "TRUE", "FALSE": "FALSE",
            "MISLEADING": "MISLEADING", "PARTIALLY_TRUE": "PARTIALLY_TRUE",
            "INSUFFICIENT_EVIDENCE": "INSUFFICIENT_EVIDENCE",
        }.get(verdict_str, "UNVERIFIED")

        raw_conf = investigation_res.get("confidence")
        conf_int = int(raw_conf * 100) if (raw_conf is not None and raw_conf <= 1.0) else (int(raw_conf) if raw_conf is not None else None)
        hawkes_r0 = None  # Hawkes R0 requires actual time-series event sequence observations

        # Category detection
        lower_claim = norm_text.lower()
        if any(w in lower_claim for w in ["stock", "shares", "nasdaq", "sec", "bank", "crypto", "billion", "market"]):
            category = "FINANCIAL THREAT INTELLIGENCE"
        elif any(w in lower_claim for w in ["cancer", "vaccine", "cure", "health", "doctor", "hospital", "disease", "5g"]):
            category = "HEALTH & SCIENTIFIC ADVISORY"
        elif any(w in lower_claim for w in ["deepfake", "video", "audio", "leak", "secret", "impersonat"]):
            category = "SYNTHETIC MEDIA & DEEPFAKE"
        elif any(w in lower_claim for w in ["election", "president", "war", "minister", "military", "border"]):
            category = "GEOPOLITICAL INTELLIGENCE"
        else:
            category = "GLOBAL INFORMATION FORENSICS"

        # Evidence Formatting with Relevance Gate Filtering
        from backend.services.research.relevance_gate import relevance_gate
        rejected_claim_evidence = []

        def inspectable(item):
            try:
                parsed = urllib.parse.urlsplit(str(item.get("url") or ""))
                return (parsed.scheme in ("http", "https") and bool(parsed.hostname)
                        and not parsed.username and not parsed.password
                        and bool(str(item.get("text") or "").strip()))
            except ValueError:
                return False

        supporting_list = []
        for s in evidence_json.get("supporting_evidence", []):
            text_val = (s.get("text") or s.get("quote") or s.get("summary") or "") if isinstance(s, dict) else str(s)
            title_val = (s.get("title") or s.get("source") or text_val[:60]) if isinstance(s, dict) else text_val[:60]
            url_val = s.get("url") if isinstance(s, dict) else None
            
            assess = relevance_gate.evaluate_item(
                type("Item", (), {"id": "sup", "title": title_val, "snippet": text_val, "url": url_val or ""})(),
                target_entity=norm_text,
                domain="fact_check"
            )
            if not assess.is_accepted:
                rejected_claim_evidence.append(assess.to_dict())
                logger.info(f"[VerifySync] Rejecting off-topic supporting item: {assess.rejection_reason}")
                continue

            # A model-generated sentence is not an independently inspectable
            # source. Keep it out of the evidence and replay lineage.
            if not (isinstance(s, dict) and inspectable({"url": url_val, "text": text_val})):
                rejected_claim_evidence.append({"reason": "MISSING_SOURCE_LINK", "stance": "supporting"})
                continue

            if isinstance(s, dict):
                supporting_list.append({
                    "source": s.get("source") or s.get("source_name"),
                    "platform": s.get("platform"),
                    "text": text_val,
                    "url": url_val
                })

        refuting_list = []
        for r in evidence_json.get("refuting_evidence", []):
            text_val = (r.get("text") or r.get("quote") or r.get("summary") or "") if isinstance(r, dict) else str(r)
            title_val = (r.get("title") or r.get("source") or text_val[:60]) if isinstance(r, dict) else text_val[:60]
            url_val = r.get("url") if isinstance(r, dict) else None

            assess = relevance_gate.evaluate_item(
                type("Item", (), {"id": "ref", "title": title_val, "snippet": text_val, "url": url_val or ""})(),
                target_entity=norm_text,
                domain="fact_check"
            )
            if not assess.is_accepted:
                rejected_claim_evidence.append(assess.to_dict())
                logger.info(f"[VerifySync] Rejecting off-topic refuting item: {assess.rejection_reason}")
                continue

            if not (isinstance(r, dict) and inspectable({"url": url_val, "text": text_val})):
                rejected_claim_evidence.append({"reason": "MISSING_SOURCE_LINK", "stance": "refuting"})
                continue

            if isinstance(r, dict):
                refuting_list.append({
                    "source": r.get("source") or r.get("source_name"),
                    "platform": r.get("platform"),
                    "text": text_val,
                    "url": url_val
                })

        evidence_backed = any(inspectable(item) for item in supporting_list + refuting_list)
        if not evidence_backed:
            clean_verdict = "INSUFFICIENT_EVIDENCE"
            conf_int = None
            explanation = "The research response supplied no source-linked passage to substantiate a verdict."
        else:
            explanation = investigation_res.get("reasoning") or "No conclusive explanation was supplied."

        debunk_stmt = (f"Aegis Fact-Check: Evidence-linked assessment of '{norm_text[:60]}...' is {clean_verdict}. {explanation[:120]}"
                       if clean_verdict in ("TRUE", "FALSE", "MISLEADING", "PARTIALLY_TRUE") else None)
        duration = round(time.perf_counter() - start_time, 2)

        # Database cache insertion
        try:
            existing = db.get_claim_by_hash(claim_hash)
            if not existing:
                db.insert_claim(claim_hash=claim_hash, claim_text=claim_raw, normalized_text=norm_text)
                db.update_claim_status(claim_id=claim_hash, status="completed")
                db.update_claim_verdict(
                    claim_id=claim_hash,
                    verdict=clean_verdict,
                    confidence=conf_int,
                    severity=investigation_res.get("severity", "Medium"),
                    reasoning=explanation
                )
        except Exception as e_db:
            logger.debug(f"[VerifySync] Database cache note: {e_db}")

        social_radar = {
            "reddit": {
                "mentions": len(reddit_items),
                "sentiment": None,
                "top_sub": reddit_items[0].get("subreddit") if reddit_items else None,
                "summary": reddit_items[0].get("title") if reddit_items else None
            },
            "twitter": {
                "virality": "Unmeasured (no time-series stream)",
                "bot_ratio": "Unmeasured",
                "cashtag": None,
                "mentions": len(twitter_items)
            },
            "youtube": {
                "video_count": len(youtube_items),
                "finding": youtube_items[0].get("title") if youtube_items else None
            },
            "news": {
                "registry_status": "RESULTS_RETURNED" if news_items else "NOT_VERIFIED",
                "top_wire": news_items[0].get("source") if news_items else None,
                "articles_count": len(news_items)
            },
            "raw_signals": {
                "reddit": reddit_items[:4],
                "twitter": twitter_items[:4],
                "youtube": youtube_items[:4],
                "news": news_items[:4]
            }
        }

        # Construct Source Lineage DAG for claim evidence
        lineage_candidates: List[EvidenceItem] = []
        for idx, s in enumerate(supporting_list + refuting_list):
            cand_url = s.get("url") or s.get("canonical_url") or ""
            cand_source = s.get("source") or s.get("source_name") or "Unknown Source"
            cand_text = s.get("text") or s.get("snippet") or ""
            lineage_candidates.append(EvidenceItem(
                id=f"ev_claim_{idx+1}",
                canonical_url=cand_url,
                title=cand_source,
                source_name=cand_source,
                snippet=cand_text,
                source_tier=SourceTier.TIER_3_AGGREGATE.value,
                source_role=SourceRole.DISCOVERY.value,
                primary_source=False,
                relevance_score=s.get("relevance_score") or 0.50
            ))

        lineage_engine = SourceLineageEngine()
        lineage_graph = lineage_engine.build_lineage_graph(lineage_candidates)
        # The shared legacy metric is a count of nodes without detected echo
        # edges, not demonstrated independence. Scope the honest disclosure
        # to claim responses without rewriting historical Phase 4 goldens.
        lineage_graph["metrics"]["candidate_non_echo_count"] = lineage_graph["metrics"]["true_independent_count"] if lineage_candidates else 0
        lineage_graph["metrics"]["true_independent_count"] = None if lineage_candidates else 0
        lineage_graph["metrics"]["independence_status"] = "UNVERIFIED_HEURISTIC" if lineage_candidates else "NO_EVIDENCE"

        genuine_corpus = evidence_json.get("research_corpus")
        rc_dict = genuine_corpus if isinstance(genuine_corpus, dict) else {}
        genuine_tensor = None
        if isinstance(genuine_corpus, dict) and genuine_corpus.get("findings"):
            for f in genuine_corpus["findings"]:
                if isinstance(f, dict) and f.get("quality_tensor"):
                    genuine_tensor = f["quality_tensor"]
                    break
        elif isinstance(evidence_json.get("quality_tensor"), dict):
            genuine_tensor = evidence_json["quality_tensor"]

        quality_status = "VERIFIED_CORPUS" if genuine_tensor is not None else "UNAVAILABLE_NO_CORPUS"

        # Register immutable research dossier into ReplayLedger
        session_id = replay_ledger.record_investigation(
            target=norm_text,
            domain="fact_check",
            summary=explanation,
            candidates=lineage_candidates,
            findings=[{
                "finding_id": "FND-01",
                "title": norm_text[:100],
                "epistemic_state": "KNOWN_FACT" if clean_verdict == "TRUE" else ("REFUTED" if clean_verdict == "FALSE" else "UNVERIFIED"),
                "quality_tensor": genuine_tensor,
                "quality_status": quality_status,
                "supporting_evidence_ids": [f"ev_claim_{i+1}" for i in range(len(supporting_list))],
                "contradicting_evidence_ids": [f"ev_claim_{len(supporting_list)+i+1}" for i in range(len(refuting_list))],
                "primary_sources": [c.canonical_url for c in lineage_candidates if c.primary_source],
            }],
            queries=rc_dict.get("query_log") or [],
            telemetry={"total_latency_ms": int(duration * 1000), "execution_graph": []},
            lineage_graph=lineage_graph
        )

        resp_payload = {
            "status": "success",
            "claim": norm_text,
            "claim_hash": claim_hash,
            "session_id": session_id,
            "quality_tensor": genuine_tensor,
            "quality_status": quality_status,
            "replay_url": f"/api/research/replay/dossiers/{session_id}",
            "source_lineage": lineage_graph,
            "verdict": clean_verdict,
            "confidence": conf_int,
            "severity": investigation_res.get("severity", "Medium"),
            "category": category,
            "explanation": explanation,
            "atomic_claims": [c.to_dict() if hasattr(c, "to_dict") else c for c in atomic_claims],
            "evidence_chain": investigation_res.get("evidence_chain", []),
            "research_trace": evidence_json.get("research_trace", {}),
            "contradictions": evidence_json.get("contradictions", []),
            "primary_sources": evidence_json.get("primary_sources", []),
            "supporting_evidence": supporting_list,
            "refuting_evidence": refuting_list,
            "rejected_evidence": rejected_claim_evidence,
            "social_radar": social_radar,
            "forensic_risk": {
                "mandelbrot_r2": mandel_r2,
                "synthetic_marker": "Unusual Text Frequency Correlation" if (mandel_r2 is not None and mandel_r2 >= 0.90) else ("Standard Lexical Distribution" if mandel_r2 is not None else "Insufficient Tokens"),
                "hawkes_r0": None,
                "hawkes_status": "UNAVAILABLE",
                "hawkes_reason": "No time-series event sequence observations available",
                "entropy_bits": entropy,
                "polarization_score": None,
                "polarization_status": "UNAVAILABLE",
                "polarization_reason": "No sentiment-polarized discourse corpus available"
            },
            "debunk_statement": debunk_stmt,
            "action_package": ({"copy_debunk": debunk_stmt} if debunk_stmt else None),
            "execution_time_seconds": duration,
            "agents_executed": ["ClaimIngestionAgent", "ResearchAgent", "InvestigatorAgent"],
            "claim_id": claim_hash,
            "funnel": rc_dict.get("funnel") or {
                "queries_planned": 0,
                "queries_executed": 0,
                "candidates_found": len(lineage_candidates),
                "unique_candidates": len(lineage_candidates),
                "deep_reads_count": 0,
                "primary_sources_count": sum(1 for c in lineage_candidates if c.primary_source),
                "independent_groups_count": None,
                "contradictions_count": len(evidence_json.get("contradictions", [])),
                "findings_count": 1 if lineage_candidates else 0,
                "saturation_score": None,
                "halt_reason": "UNAVAILABLE_NO_CORPUS",
            },
            "findings": rc_dict.get("findings") or ([{
                "finding_id": "FND-01",
                "title": norm_text[:80],
                "statement": explanation,
                "epistemic_state": "KNOWN_FACT" if clean_verdict == "TRUE" else ("REFUTED" if clean_verdict == "FALSE" else "UNVERIFIED"),
                "supporting_evidence_ids": [f"ev_claim_{i+1}" for i in range(len(supporting_list))],
                "contradicting_evidence_ids": [f"ev_claim_{len(supporting_list)+i+1}" for i in range(len(refuting_list))],
                "quality_tensor": None,
            }] if lineage_candidates else []),
            "sources": [c.to_dict() for c in lineage_candidates],
            "candidate_selection_audit": rc_dict.get("candidate_selection_audit") or [],
            "channel_telemetry": rc_dict.get("channel_telemetry") or {},
            "research_funnel": db.get_claim_research_funnel(claim_hash) or (rc_dict.get("funnel") if evidence_json.get("research_corpus") else None),
            "has_research_corpus": bool(evidence_json.get("research_corpus")),
            "research_url": f"/api/claims/{claim_hash}/research" if evidence_json.get("research_corpus") else None
        }

        if evidence_json.get("research_corpus"):
            db.save_claim_research(claim_hash, evidence_json["research_corpus"])

        # ── Unified Report (schema v3.8.0) ────────────────────────────────────
        try:
            _unified = ReportBuilder.from_claim_result(
                claim_text=norm_text,
                verdict={**investigation_res, "verdict": clean_verdict, "confidence": conf_int, "reasoning": explanation, "explanation": explanation} if isinstance(investigation_res, dict) else None,
                corpus=None,  # structured corpus not yet wired through evidence_json path
                execution_log=rc_dict.get("query_log") or [],
                queries_planned=len(rc_dict.get("query_log") or []),
            )
            resp_payload["unified_report"] = _unified.to_dict()
        except Exception as _ur_err:
            logger.warning(f"[VerifySync] unified_report assembly note: {_ur_err}")
            resp_payload["unified_report"] = None

        return resp_payload
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[API] verify_claim_sync critical error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Claim verification failed: {str(e)}")


@router.post("/api/claims/submit", response_model=ClaimSubmitResponse, summary="Async Claim Ingestion & Queuing")
@router.post("/api/claims", response_model=ClaimSubmitResponse)
@router.post("/api/claims/", response_model=ClaimSubmitResponse)
@router.post("/api/ingest", response_model=ClaimSubmitResponse)
@router.post("/api/submit", response_model=ClaimSubmitResponse)
def submit_claim(request: ClaimSubmitRequest, background_tasks: BackgroundTasks):
    """
    Submit a claim for fact-checking via background task.
    """
    logger.info(f"[API] POST /claims/submit - Claim: {request.claim_text[:50]}...")

    try:
        claim_ingestion_agent = get_claim_ingestion_agent()
        ingest_result = claim_ingestion_agent.ingest(
            claim_text=request.claim_text,
            source_url=request.source_url
        )

        claim_id = str(ingest_result["claim_id"])
        is_new = bool(ingest_result.get("is_new", True))
        status = str(ingest_result.get("status", "pending"))

        if is_new:
            logger.info(f"[API] Dispatching background investigation for claim ID: {claim_id}")
            background_tasks.add_task(process_claim, claim_id)
        else:
            logger.info(f"[API] Existing claim returned immediately (ID: {claim_id}, status: {status})")

        return ClaimSubmitResponse(
            claim_id=claim_id,
            status=status,
            is_new=is_new
        )

    except Exception as e:
        logger.error(f"[API] Error submitting claim: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing claim: {str(e)}")


@router.get("/api/claims/{claim_id}", summary="Get Claim Status & Results by ID")
def get_claim_status(claim_id: str):
    """Get status and results of a claim by ID."""
    logger.info(f"[API] GET /claims/{claim_id}")
    try:
        claim = db.get_claim_by_id(claim_id)
        if not claim:
            raise HTTPException(status_code=404, detail=f"Claim not found: {claim_id}")

        evidence_list = db.get_evidence_by_claim_id(claim_id)
        research_funnel = db.get_claim_research_funnel(claim_id)
        has_corpus = bool(db.get_claim_research(claim_id))
        return {
            "claim_id": claim_id,
            "claim_hash": claim.get("claim_hash"),
            "claim_text": claim.get("claim_text"),
            "normalized_text": claim.get("normalized_text"),
            "status": claim.get("status"),
            "verdict": claim.get("verdict"),
            "confidence": claim.get("confidence"),
            "confidence_score": claim.get("confidence"),
            "severity": claim.get("severity"),
            "reasoning": claim.get("reasoning"),
            "evidence": evidence_list,
            "research_funnel": research_funnel,
            "has_research_corpus": has_corpus,
            "research_url": f"/api/claims/{claim_id}/research" if has_corpus else None,
            "created_at": claim.get("created_at"),
            "updated_at": claim.get("updated_at")
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[API] Error retrieving claim: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving claim: {str(e)}")


@router.get("/api/claims/{claim_id}/research", summary="Get Full Forensic Research Corpus by Claim ID")
def get_claim_research_corpus(claim_id: str):
    """
    Dedicated endpoint returning the complete ResearchCorpus for a claim.
    Includes planned queries, candidate selection audit, deep read sources with
    extracted passages, primary escalations, syndication clusters, contradictions,
    grounded findings, and evidence graph.
    """
    logger.info(f"[API] GET /claims/{claim_id}/research")
    try:
        corpus = db.get_claim_research(claim_id)
        if not corpus:
            claim = db.get_claim_by_id(claim_id)
            if not claim:
                raise HTTPException(status_code=404, detail=f"Claim not found: {claim_id}")
            raise HTTPException(
                status_code=404,
                detail=f"Research corpus not yet generated for claim: {claim_id}. Current status is '{claim.get('status')}'."
            )

        funnel = db.get_claim_research_funnel(claim_id) or corpus.get("funnel") or {}
        return {
            "claim_id": claim_id,
            "funnel": funnel,
            "corpus": corpus,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[API] Error retrieving claim research corpus: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving research corpus: {str(e)}")


@router.get("/api/claims", summary="List All Claims with Pagination")
def list_all_claims(limit: int = 50, offset: int = 0):
    """List all claims in the system with pagination."""
    logger.info(f"[API] GET /claims - limit={limit}, offset={offset}")
    try:
        if db.supabase:
            response = db.supabase.table("claims") \
                .select("id, claim_text, status, verdict, created_at") \
                .range(offset, offset + limit - 1) \
                .execute()
            claims_list = response.data if response.data else []
        else:
            all_c = db.get_all_claims(limit=limit + offset)
            claims_list = all_c[offset:offset + limit]

        return {"total_claims": len(claims_list), "limit": limit, "offset": offset, "claims": claims_list}
    except Exception as e:
        logger.error(f"[API] Error listing claims: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error listing claims: {str(e)}")


@router.get("/api/claims/{claim_id}/evidence", summary="Get Evidence for Claim")
def get_claim_evidence(claim_id: str):
    """Get all supporting and refuting evidence records linked to a claim."""
    try:
        claim = db.get_claim_by_id(claim_id)
        if not claim:
            raise HTTPException(status_code=404, detail="Claim not found")
        ev_list = db.get_evidence_by_claim_id(claim_id)
        return {"claim_id": claim_id, "count": len(ev_list), "evidence": ev_list}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[API] Error fetching evidence for {claim_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
