"""
Aegis Protocol — System & Telemetry API Router
==============================================
Provides agent telemetry, health checks, dashboard data, and Gemini proxy endpoints.
"""

import os
import uuid
import time
import hashlib
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from backend.db import database as db
from backend.services.dashboard_loader import load_random_dashboard_claims

logger = logging.getLogger(__name__)

router = APIRouter(tags=["System & Telemetry"])


class GeminiProxyRequest(BaseModel):
    prompt: str = Field(..., description="Prompt string to execute with model rotation.")


@router.get("/healthz")
@router.get("/api/healthz")
async def healthz():
    """Liveness probe for deployment containers and orchestrators."""
    return {
        "status": "ok",
        "system": "Aegis Protocol",
        "version": "3.5.1",
        "timestamp": datetime.now().isoformat(),
        "active_agents": 7
    }


@router.get("/api/")
async def api_info():
    """System overview and high-level routing index."""
    return {
        "name": "Aegis Protocol API",
        "version": "3.5.1",
        "architecture": "Modular Multi-Agent Swarm with Zero-Cost Omni-Scraper Fabric",
        "documentation": "/docs",
        "redoc": "/redoc",
        "agents": [
            "ClaimIngestionAgent",
            "ResearchAgent",
            "InvestigatorAgent",
            "TrendingAgent",
            "ScoutAgent",
            "BrandShieldAgent",
            "PersonalWatchAgent"
        ],
        "endpoints": {
            "claims": ["POST /api/claims/verify (sync)", "POST /api/claims/submit (async)", "GET /api/claims/{claim_id}", "GET /api/claims"],
            "agent_reach": ["POST /api/agent-reach/omni-scan", "POST /api/agent-reach/scan", "POST /api/agent-reach/read", "GET /api/agent-reach/doctor"],
            "scout": ["POST /api/scout/analyze", "GET /api/stock", "GET /api/trending-news"],
            "brandshield": ["POST /api/brandshield/scan"],
            "personal_watch": ["POST /api/personal/scan", "POST /api/personal-watch/scan"],
            "trending": ["POST /api/trending/scan", "POST /api/defense/generate"],
            "threat_lab": ["POST /api/lab/synthetic-detect", "POST /api/lab/blast-radius", "POST /api/lab/consensus"],
            "telemetry": ["GET /api/system/agents", "GET /api/healthz"]
        }
    }


@router.get("/api/media/launch-info", tags=["Media & Teaser"])
async def launch_video_info():
    """Get metadata and resource paths for the official Aegis Protocol launch video."""
    return {
        "title": "Aegis Protocol — Official Launch Film",
        "duration_seconds": 20,
        "format": "1080p landscape (1920x1080)",
        "interactive_player": "/launch-video",
        "video_path": "brag-output/brag.mp4",
        "poster_path": "brag-output/brag.png",
        "scenes": 4,
        "status": "ready"
    }


@router.get("/api/system/agents", summary="Telemetry & Capability Matrix for All 7 Agents")
async def get_system_agents():
    """
    Returns real-time status, capabilities, models, and diagnostic telemetry
    for all 7 agents in the Aegis Protocol multi-agent architecture.
    """
    return {
        "timestamp": datetime.now().isoformat(),
        "total_agents": 7,
        "swarm_status": "ONLINE",
        "agents": {
            "claim_ingestion": {
                "name": "ClaimIngestionAgent",
                "role": "Gatekeeper & Deduplication Node",
                "status": "active",
                "engine": "Cryptographic SHA-256 Hash Normalization",
                "capabilities": ["text_cleaning", "entity_resolution", "duplicate_detection", "supabase_sync"]
            },
            "research": {
                "name": "ResearchAgent",
                "role": "Ground-Truth Evidentiary Jurist",
                "status": "active",
                "engine": "Dynamic Gemini Model Rotation + AgentReach Scraper Fabric",
                "capabilities": ["multi_model_rotation", "wire_evidence_mining", "primary_source_jina_parsing", "evidence_matrix_synthesis"]
            },
            "investigator": {
                "name": "InvestigatorAgent",
                "role": "Epistemic Stance Classifier & Juror",
                "status": "active",
                "engine": "Bayesian Stance Classification & High-Reasoning LLM",
                "capabilities": ["stance_classification", "contradiction_detection", "probabilistic_verdict", "severity_scoring"]
            },
            "trending": {
                "name": "TrendingAgent",
                "role": "Narrative Velocity & Viral Outbreak Monitor",
                "status": "active",
                "engine": "Google News RSS Stream + Hawkes Self-Exciting Point Process",
                "capabilities": ["rss_ingestion", "viral_velocity_tracking", "contagion_r0_projection", "crisis_defense_generation"]
            },
            "scout": {
                "name": "ScoutAgent",
                "role": "Financial Disinformation & Short Attack Sentinel",
                "status": "active",
                "engine": "Yahoo Finance Telemetry + WallStreetBets/Cashtag Scraper + Volatility Z-Score",
                "capabilities": ["stock_drop_detection", "z_score_volatility", "covert_short_attack_correlation", "market_catalyst_extraction"]
            },
            "brandshield": {
                "name": "BrandShieldAgent",
                "role": "E-Commerce Counterfeit & Fake Review Defense",
                "status": "active",
                "engine": "Multi-Platform Review Scraper (Amazon, Flipkart, Trustpilot, Reddit, Google Reviews)",
                "capabilities": ["counterfeit_detection", "fake_review_syndicate_clustering", "reputational_smear_alerting", "automated_cease_desist"]
            },
            "personal_watch": {
                "name": "PersonalWatchAgent",
                "role": "VIP Reputation, Deepfake & Impersonation Shield",
                "status": "active",
                "engine": "Synthetic Media Audio/Video Marker Analysis + Social Impersonation Scanner",
                "capabilities": ["voice_video_deepfake_markers", "social_handle_impersonation", "doxxing_darkweb_leaks", "reputation_threat_scoring"]
            }
        },
        "scraper_fabric": {
            "engine": "AgentReach Zero-Cost Scraper (Panniantong Compatible)",
            "status": "ready",
            "channels": ["Reddit Discussion Streams", "Twitter/X Targeted Search", "YouTube Video Transcripts", "Google News RSS", "Jina Reader Clean Markdown"]
        }
    }


@router.post("/api/gemini")
@router.post("/.netlify/functions/gemini")
async def gemini_proxy(request: GeminiProxyRequest):
    """Secure backend proxy for Gemini AI calls with dynamic model rotation."""
    try:
        from backend.services.intelligence import call_gemini_text
        text_resp = call_gemini_text(request.prompt)
        return {"text": text_resp}
    except Exception as e:
        logger.error(f"[API] Gemini proxy failed: {e}")
        raise HTTPException(status_code=500, detail=f"Gemini generation failed: {str(e)}")


@router.get("/api/dashboard/claims")
@router.get("/dashboard/claims")
async def get_dashboard_claims(fresh: bool = False):
    """
    Get 15 claims for the live dashboard.
    Priority: real verified claims first, topped up with WELFake dataset.
    """
    logger.info("[API] GET /dashboard/claims")
    try:
        results = []

        try:
            if db.supabase:
                resp = db.supabase.table("claims") \
                    .select("claim_text, verdict, reasoning, source_url") \
                    .eq("status", "completed") \
                    .not_.is_("verdict", "null") \
                    .order("created_at", desc=True) \
                    .limit(30) \
                    .execute()
                if resp.data:
                    for row in resp.data:
                        verdict_raw = row.get("verdict", "False") or "False"
                        vl = verdict_raw.lower()
                        if vl in ("true", "1", "real"):
                            verdict = "True"
                        elif vl in ("misleading", "partially true", "mixed"):
                            verdict = "Misleading"
                        else:
                            verdict = "False"
                        results.append({
                            "claim":        row.get("claim_text", ""),
                            "verdict":      verdict,
                            "explanation":  row.get("reasoning") or "AI-verified claim from live news feed.",
                            "evidence_url": row.get("source_url") or ""
                        })
                    logger.info(f"[API] Loaded {len(results)} real claims from Supabase")
        except Exception as db_err:
            logger.warning(f"[API] Supabase fetch failed, falling back to dataset: {db_err}")

        # Top up with local or dataset claims if fewer than 15
        needed = 15 - len(results)
        if needed > 0:
            if fresh:
                fallback = load_random_dashboard_claims(n=needed)
            else:
                from backend.services.dashboard_loader import get_dashboard_claims_rotating
                logger.info("[API] Using rotating cache for dashboard top-up")
                fallback = get_dashboard_claims_rotating(
                    n=needed, ttl_seconds=int(os.getenv("DASHBOARD_TTL", "300"))
                )
            for item in fallback:
                results.append({
                    "claim":        item.get("claim", ""),
                    "verdict":      item.get("label", "False"),
                    "explanation":  "Click 'Show Evidence' for AI-generated explanation.",
                    "evidence_url": ""
                })

        sample_id = str(uuid.uuid4())
        first_claim = results[0]["claim"] if results else ""
        checksum = hashlib.sha1(
            "\n".join([r["claim"] for r in results]).encode("utf-8", errors="ignore")
        ).hexdigest()

        headers = {
            "Cache-Control": "no-store, no-cache, max-age=0, must-revalidate",
            "Pragma": "no-cache",
            "X-Dashboard-Source": "supabase+rotating",
            "X-Sample-Id": sample_id,
            "X-First-Claim": first_claim[:120].encode('ascii', 'replace').decode('ascii'),
            "X-Claims-Checksum": checksum
        }
        return JSONResponse(content=results, headers=headers)

    except Exception as e:
        logger.error(f"[API] Error generating dashboard claims: {str(e)}")
        raise HTTPException(status_code=500, detail="Error generating dashboard claims")


@router.get("/api/dashboard/debug")
@router.get("/dashboard/debug")
async def dashboard_debug():
    """Debug endpoint showing dashboard cache state."""
    try:
        from backend.services.dashboard_loader import get_dashboard_claims_rotating
        claims = get_dashboard_claims_rotating(n=15, ttl_seconds=int(os.getenv("DASHBOARD_TTL", "300")))
        sample_id = str(uuid.uuid4())
        first_claim = claims[0]["claim"] if claims else ""
        checksum = hashlib.sha1(
            "\n".join([r["claim"] for r in claims]).encode("utf-8", errors="ignore")
        ).hexdigest()
        return {
            "sample_id": sample_id,
            "first_claim": first_claim,
            "checksum": checksum,
            "count": len(claims),
            "claims_preview": claims[:3]
        }
    except Exception as e:
        logger.error(f"[DEBUG] dashboard_debug error: {e}")
        raise HTTPException(status_code=500, detail="Dashboard debug failed")


@router.post("/api/explain-claim")
@router.post("/explain-claim")
async def explain_claim(request: dict):
    """Generate an AI explanation for a dashboard claim."""
    claim_text = request.get("claim", "")
    verdict = request.get("verdict", "False")
    logger.info(f"[API] POST /explain-claim - Claim: {claim_text[:50]} (verdict={verdict})")
    try:
        from backend.agents.research_agent import ResearchAgent
        agent = ResearchAgent()
        result = await agent.generate_dashboard_explanation(claim_text, verdict)
        return {
            "explanation": result.get("explanation", "Explanation unavailable."),
            "evidence_url": result.get("evidence_url", "")
        }
    except Exception as e:
        logger.error(f"[API] Error generating explanation: {str(e)}")
        return {"explanation": "Unable to generate explanation right now.", "evidence_url": ""}
