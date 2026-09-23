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
    Developer diagnostics endpoint providing complete retrieval execution telemetry.
    Shows planned queries, executed channel queries, raw vs final counts, deduplication losses,
    latency breakdown, and failure reasons.
    """
    logger.info(f"[API] POST /api/agent-reach/debug - query='{request.query}' domain='{request.domain}'")
    try:
        clean_q = request.query.strip()
        plan = agent_reach_service.planner.plan(clean_q, domain=request.domain or "general")

        result = agent_reach_service.retrieve_many(
            channel_queries=plan.multi_channel_queries,
            domain=request.domain or "general",
            agent_name="debug_debugger",
            target_name=clean_q,
            budget={
                "max_queries_per_channel": request.max_queries_per_channel or 3,
                "max_results_per_query": request.limit_per_query or 4,
                "max_total_evidence": 50,
                "max_deep_reads": 4,
            },
            perform_reads=request.perform_reads,
            timeout=12.0
        )

        trace = result.retrieval_trace or {}
        channels_stat = trace.get("channels", {})
        total_stat = trace.get("total", {})

        # Build clean formatted ASCII report string
        lines = []
        lines.append(f"SCAN: {clean_q} (domain={request.domain})")
        lines.append("────────────────────────────────────────────")
        lines.append(f"Query classes planned: {trace.get('planning', {}).get('query_classes_created', 0)}")
        lines.append(f"Queries executed:      {trace.get('planning', {}).get('queries_executed', 0)}")
        lines.append("")
        lines.append(f"{'CHANNEL':<15} {'RAW':<8} {'FINAL':<8} {'STATUS':<12}")
        lines.append("────────────────────────────────────────────")
        for ch, s in channels_stat.items():
            lines.append(f"{ch:<15} {s.get('raw_results', 0):<8} {s.get('final_results', 0):<8} {s.get('status', 'OK'):<12}")
        lines.append("────────────────────────────────────────────")
        lines.append(f"{'RAW TOTAL:':<15} {total_stat.get('raw_results', 0)}")
        lines.append(f"{'DUPLICATES:':<15} {total_stat.get('duplicates_removed', 0)}")
        lines.append(f"{'FINAL EVIDENCE:':<15} {total_stat.get('final_evidence', 0)}")
        lines.append(f"{'READABLE:':<15} {total_stat.get('readable_sources', 0)}")
        lines.append(f"{'INDEP GROUPS:':<15} {total_stat.get('independent_groups', 0)}")

        return {
            "scan": {
                "query": clean_q,
                "domain": request.domain,
                "scan_id": trace.get("scan_id"),
            },
            "planning": {
                "query_classes_count": trace.get("planning", {}).get("query_classes_created", 0),
                "queries_generated": trace.get("planning", {}).get("queries_generated", 0),
                "queries_executed": trace.get("planning", {}).get("queries_executed", 0),
                "query_classes": plan.query_classes,
            },
            "execution": {
                ch: [q["query_text"] for q in q_list]
                for ch, q_list in plan.multi_channel_queries.items()
            },
            "channels": channels_stat,
            "total": total_stat,
            "raw_evidence_sample": [
                {
                    "channel": f.channel_name or f.platform,
                    "query_class": f.query_class,
                    "query_text": f.query_text,
                    "title": f.title,
                    "url": f.url,
                    "snippet": f.snippet,
                    "content_depth": f.content_depth,
                    "retrieval_method": f.retrieval_method,
                }
                for f in result.fragments[:15]
            ],
            "formatted_telemetry": "\n".join(lines),
        }
    except Exception as e:
        logger.error(f"[API] AgentReach debug failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
