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
    """Run diagnostics across all internet evidence channels (Reddit, Twitter, YouTube, News, Jina, GitHub, RSS)."""
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
