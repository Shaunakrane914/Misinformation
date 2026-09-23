"""
Aegis Protocol — Agent Reach Capability Layer API Router
=========================================================
Endpoints for omni-channel internet evidence acquisition:
- Capability discovery & health probes
- Domain-directed retrieval scans
- Unified multi-platform scans
- SSRF-safe dynamic webpage reading via Jina Reader
"""

import logging
import time
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.services.agent_reach import agent_reach_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/agent-reach", tags=["Agent Reach (Omni-Channel Scrapers)"])


# ── Request Models ───────────────────────────────────────────────────────────

class OmniScanRequest(BaseModel):
    query: str = Field(
        ...,
        description="Target query, company, person, product, or narrative to extract.",
        json_schema_extra={"example": "Nvidia Blackwell AI chip delay packaging defect"}
    )
    domain: Optional[str] = Field(
        "general",
        description="Target domain: 'financial' | 'fact_check' | 'brand' | 'personal' | 'trending' | 'general'",
        json_schema_extra={"example": "financial"}
    )
    source_url: Optional[str] = Field(
        None,
        description="Optional URL to scrape with Jina Reader in parallel.",
        json_schema_extra={"example": "https://www.bloomberg.com"}
    )
    vip_handle: Optional[str] = Field(
        None,
        description="Optional handle for personal impersonation verification.",
        json_schema_extra={"example": "@sama"}
    )
    limit: Optional[int] = Field(4, description="Max items per channel.")


class AgentReachScanRequest(BaseModel):
    query: str = Field(
        ...,
        description="Keyword or topic to scan across multi-platform feeds.",
        json_schema_extra={"example": "OpenAI Orion reasoning model leak"}
    )
    include_reddit: Optional[bool] = Field(True, description="Search Reddit public discussion streams.")
    include_twitter: Optional[bool] = Field(True, description="Search Twitter/X syndication & search streams.")
    include_youtube: Optional[bool] = Field(True, description="Search YouTube video metadata and discussions.")
    include_news: Optional[bool] = Field(True, description="Search Google News RSS wire feeds.")
    limit: Optional[int] = Field(4, description="Max results per channel.")


class AgentReachReadRequest(BaseModel):
    url: str = Field(
        ...,
        description="URL of article or webpage to convert into clean Markdown via Jina Reader.",
        json_schema_extra={"example": "https://www.reuters.com/technology"}
    )
    max_chars: Optional[int] = Field(3500, description="Max characters to return.")


class AgentReachDebugRequest(BaseModel):
    query: str = Field(..., description="Entity or claim to debug retrieval on", json_schema_extra={"example": "Nike"})
    domain: Optional[str] = Field("brand", description="Domain context: brand | financial | trending | personal | fact_check | general")
    max_queries_per_channel: Optional[int] = Field(3, description="Max queries per channel")
    limit_per_query: Optional[int] = Field(4, description="Max results per query")
    perform_reads: Optional[bool] = Field(True, description="Attempt deep reading on top URLs")


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/capabilities", summary="Capability Inventory & Status")
async def agent_reach_capabilities():
    """Return channel capability inventory, supported domains, and server compatibility."""
    logger.info("[API] GET /api/agent-reach/capabilities")
    try:
        return agent_reach_service.capabilities()
    except Exception as e:
        logger.error(f"[API] AgentReach capabilities failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health", summary="Channel Health & Probe Discovery")
@router.get("/doctor", summary="Run Zero-Cost Scraper Diagnostics")
async def agent_reach_doctor():
    """Run diagnostics across all internet evidence channels (Reddit, Twitter, YouTube, News, Jina, GitHub, RSS, Web)."""
    logger.info("[API] GET /api/agent-reach/health")
    try:
        return agent_reach_service.health()
    except Exception as e:
        logger.error(f"[API] AgentReach health check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/scan", summary="Unified Cross-Platform Scan")
async def agent_reach_scan(request: AgentReachScanRequest):
    """Execute unified multi-platform scan across social media, forums, and news."""
    logger.info(f"[API] POST /api/agent-reach/scan - query={request.query}")
    try:
        return agent_reach_service.unified_scan(
            query=request.query,
            max_results_per_platform=request.limit or 5
        )
    except Exception as e:
        logger.error(f"[API] AgentReach scan failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/omni-scan", summary="Domain-Directed Omni-Channel Scraper Pass")
async def agent_reach_omni_scan(request: OmniScanRequest):
    """
    Execute domain-specialized multi-platform extraction:
    - 'financial': cashtags, volatility, panic, short-seller discourse (Scout)
    - 'fact_check': verification, debunked, official press, community consensus (Research)
    - 'brand': fake reviews, counterfeits, consumer scams (BrandShield)
    - 'personal': audio deepfakes, impersonation, reputation attacks (Personal Watch)
    - 'trending': viral memes, pop-culture velocity, hashtag spikes (Trending)
    - 'technical': code repositories, CVEs, release notes, maintainer statements (GitHub)
    """
    logger.info(f"[API] POST /api/agent-reach/omni-scan - query='{request.query}' domain='{request.domain}'")
    try:
        return agent_reach_service.omni_scan(
            query=request.query,
            domain=request.domain or "general",
            source_url=request.source_url,
            limit_per_channel=request.limit or 4
        )
    except Exception as e:
        logger.error(f"[API] Omni-scan failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/read", summary="Convert URL to Clean Markdown with SSRF Protection")
async def agent_reach_read(request: AgentReachReadRequest):
    """Cleanly parse any article or dynamic web page to markdown with SSRF defense."""
    logger.info(f"[API] POST /api/agent-reach/read - url={request.url}")
    try:
        res = agent_reach_service.read(request.url, max_chars=request.max_chars)
        if res.get("status") == "blocked_ssrf":
            raise HTTPException(status_code=400, detail=res.get("error", "URL blocked by SSRF defense"))
        return res
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[API] AgentReach read failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/debug", summary="Retrieval Reality Telemetry & Multi-Query Debugger")
async def agent_reach_debug(request: AgentReachDebugRequest):
    """
    Developer diagnostics endpoint providing complete retrieval execution telemetry (Requirement 26).
    Uses the exact same execution path as production research.
    Exposes:
    - Agent Reach version, commit, runtime, doctor snapshot
    - Query plan (classes, queries planned/executed, follow-ups)
    - Per-channel active backend, attempted queries, raw, normalized, duplicates, final, errors, fallbacks, latency
    - Research pipeline stages: ranked, read-eligible, deep-read, primary escalations, contradictions
    - Final findings, evidence, research corpus, and formatted trace
    """
    logger.info(f"[API] POST /api/agent-reach/debug - query='{request.query}' domain='{request.domain}'")
    try:
        from backend.services.research import research_engine
        from backend.services.research.research_models import ResearchRequest
        from backend.services.agent_reach.native import native_runtime, native_doctor

        clean_q = request.query.strip()
        req = ResearchRequest(
            target=clean_q,
            domain=request.domain or "general",
            agent_name="debug_diagnostics",
            deep_read_budget=4 if request.perform_reads else 0,
            timeout_seconds=15.0,
        )
        research_res = research_engine.investigate(req)

        trace = research_res.retrieval_trace or {}
        channels_stat = trace.get("channels", {})
        total_stat = trace.get("total", {})
        doctor_snap = native_doctor.get_all_status()

        # Format per-channel active backends and telemetry
        channel_diagnostics = {}
        for ch, s in channels_stat.items():
            doc_entry = doctor_snap.get(ch, {})
            channel_diagnostics[ch] = {
                "active_backend": s.get("active_backend") or doc_entry.get("active_backend") or "default",
                "attempted_queries": s.get("queries_attempted", 0),
                "raw_results": s.get("raw_results", 0),
                "normalized_results": s.get("normalized_results", 0),
                "duplicates_removed": s.get("duplicates_removed", 0),
                "final_results": s.get("final_results", 0),
                "errors": s.get("failure_reason"),
                "fallback_used": s.get("fallback_used", False),
                "fallback_backend": s.get("fallback_backend"),
                "latency_ms": s.get("latency_ms", 0),
                "status": s.get("status", "OK"),
            }

        # Build clean formatted ASCII report string
        lines = []
        lines.append(f"TARGET: {clean_q} (domain={request.domain})")
        lines.append("────────────────────────────────────────────")
        lines.append(f"Agent Reach Version:   {native_runtime.get_upstream_version()} (commit: {native_runtime.get_upstream_commit()[:8]})")
        lines.append(f"Runtime Profile:       {native_runtime.profile.value}")
        lines.append(f"Queries Planned/Exec:  {research_res.telemetry.get('queries_planned', 0)} / {trace.get('planning', {}).get('queries_executed', 0)}")
        lines.append(f"Follow-ups Executed:   {research_res.telemetry.get('follow_ups_executed', 0)}")
        lines.append("")
        lines.append(f"{'CHANNEL':<12} {'BACKEND':<14} {'RAW':<6} {'FINAL':<6} {'FALLBACK':<10} {'STATUS':<10}")
        lines.append("────────────────────────────────────────────────────────────")
        for ch, cd in channel_diagnostics.items():
            fb_str = f"YES ({cd['fallback_backend']})" if cd["fallback_used"] else "NO"
            lines.append(f"{ch:<12} {cd['active_backend']:<14} {cd['raw_results']:<6} {cd['final_results']:<6} {fb_str:<10} {cd['status']:<10}")
        lines.append("────────────────────────────────────────────────────────────")
        lines.append(f"Total Candidates Found:       {len(research_res.candidates)}")
        lines.append(f"Ranked Evidence:              {len(research_res.evidence)}")
        lines.append(f"Deep Reads (Success/Att):     {research_res.telemetry.get('deep_read_success', 0)} / {research_res.telemetry.get('deep_read_attempted', 0)}")
        lines.append(f"Primary Sources Found:        {len(research_res.primary_sources)}")
        lines.append(f"Independent Source Groups:    {research_res.telemetry.get('independent_source_groups', 0)}")
        lines.append(f"Contradictions Detected:      {len(research_res.contradictions)}")
        lines.append(f"Grounded Findings:            {len(research_res.findings)}")
        lines.append(f"Total Pipeline Latency:       {research_res.telemetry.get('total_latency_ms', 0)}ms")

        queries_exec = trace.get("planning", {}).get("queries_executed", 0) or research_res.telemetry.get("queries_executed", 1)
        raw_res = total_stat.get("raw_results", 0) or research_res.telemetry.get("raw_results_collected", len(research_res.candidates))
        final_ev = total_stat.get("final_evidence", 0) or len(research_res.evidence)
        dup_rem = total_stat.get("duplicates_removed", 0) or max(0, raw_res - final_ev)
        read_src = total_stat.get("readable_sources", 0) or research_res.telemetry.get("deep_read_attempted", 0)

        # Backward compatibility blocks
        scan_block = {
            "query": clean_q,
            "domain": request.domain or "general",
            "scan_id": trace.get("scan_id", f"scan_{int(time.time())}"),
        }
        planning_block = {
            "query_classes_count": research_res.telemetry.get("query_classes_count", 6) or 6,
            "queries_executed": queries_exec,
        }
        execution_block = {
            "channels": list(channel_diagnostics.keys()),
            "queries_attempted": queries_exec,
        }
        total_block = {
            "raw_results": raw_res,
            "duplicates_removed": dup_rem,
            "final_evidence": final_ev,
            "readable_sources": read_src,
        }

        return {
            "status": "success",
            # Backward compatibility fields
            "scan": scan_block,
            "planning": planning_block,
            "execution": execution_block,
            "total": total_block,
            "raw_evidence_sample": [e.to_dict() for e in research_res.evidence[:15]],
            # Native Agent Reach 3.0 diagnostic fields
            "agent_reach": {
                "installed": native_runtime.is_agent_reach_installed(),
                "version": native_runtime.get_upstream_version(),
                "commit": native_runtime.get_upstream_commit(),
                "runtime": native_runtime.profile.value,
                "doctor_snapshot": doctor_snap,
            },
            "query_plan": {
                "domain": request.domain,
                "query": clean_q,
                "query_classes_count": research_res.telemetry.get("query_classes_count", 0),
                "queries_planned": research_res.telemetry.get("queries_planned", 0),
                "queries_executed": queries_exec,
                "follow_ups_executed": research_res.telemetry.get("follow_ups_executed", 0),
            },
            "channels": channel_diagnostics,
            "research": {
                "candidates_found": len(research_res.candidates),
                "candidates_ranked": len(research_res.evidence),
                "read_eligible": sum(1 for c in research_res.evidence if getattr(c, "eligible_for_read", False)),
                "deep_read_attempted": research_res.telemetry.get("deep_read_attempted", 0),
                "deep_read_success": research_res.telemetry.get("deep_read_success", 0),
                "candidate_selection_audit": research_res.telemetry.get("candidate_selection_audit", []),
                "primary_escalations": research_res.telemetry.get("escalations", {}).get("escalation_queries_executed", 0),
                "primary_sources_found": len(research_res.primary_sources),
                "independent_groups": research_res.telemetry.get("independent_source_groups", 0),
                "contradictions_found": len(research_res.contradictions),
                "findings_count": len(research_res.findings),
            },
            "final": {
                "findings": [f.to_dict() for f in research_res.findings],
                "evidence_sample": [e.to_dict() for e in research_res.evidence[:15]],
                "research_corpus": research_res.research_corpus or {},
            },
            "formatted_telemetry": "\n".join(lines),
        }
    except Exception as e:
        logger.error(f"[API] AgentReach debug failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
