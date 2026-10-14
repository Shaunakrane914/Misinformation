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

from backend import __version__
from backend.db import database as db
from backend.services.dashboard_loader import load_random_dashboard_claims

logger = logging.getLogger(__name__)

router = APIRouter(tags=["System & Telemetry"])


class GeminiProxyRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=20000, description="Prompt string to execute with model rotation.")


def normalize_dashboard_verdict(value: Any) -> str:
    """Preserve uncertainty instead of treating every unfamiliar label as false."""
    normalized = str(value or "").strip().lower().replace("_", " ")
    return {
        "true": "True", "1": "True", "real": "True",
        "false": "False", "0": "False", "fake": "False",
        "misleading": "Misleading", "partially true": "Misleading", "mixed": "Misleading",
        "unverified": "Unverified", "insufficient evidence": "Insufficient Evidence",
    }.get(normalized, "Unverified")


@router.get("/healthz")
@router.get("/api/healthz")
async def healthz():
    """Liveness probe for deployment containers and orchestrators."""
    return {
        "status": "ok",
        "system": "Aegis Protocol",
        "version": __version__,
        "response_generated_at": datetime.utcnow().isoformat() + "Z",
        "registered_modules": 7,
        "active_agents": None,
        "active_agent_count_status": "NOT_APPLICABLE_ON_DEMAND_EXECUTION"
    }


@router.get("/readyz")
@router.get("/api/readyz")
async def readyz():
    """Process readiness plus honest, non-probing acquisition state."""
    from backend.services.agent_reach.native.operation_capabilities import (
        runtime_operation_capabilities,
    )

    inventory = runtime_operation_capabilities.inventory()
    operations = [operation for channel in inventory.values() for operation in channel.values()]
    eligible = sum(1 for operation in operations if operation["decision"] != "EXCLUDE")
    verified = sum(
        1 for operation in operations
        if operation["runtime_health"] in {"HEALTHY", "LIMITED"}
    )
    return {
        "status": "ready" if eligible else "not_ready",
        "mode": "READY_WITH_VERIFIED_OPERATIONS" if verified else "READY_UNVERIFIED",
        "version": __version__,
        "operation_summary": {
            "total": len(operations),
            "eligible": eligible,
            "verified": verified,
            "auth_required": sum(
                1 for operation in operations
                if operation["runtime_health"] == "AUTH_REQUIRED"
            ),
            "policy_blocked": sum(
                1 for operation in operations
                if operation["runtime_health"] == "BLOCKED"
            ),
            "not_implemented": sum(
                1 for operation in operations
                if operation["runtime_health"] == "UNAVAILABLE_NOT_IMPLEMENTED"
            ),
        },
        "note": "Readiness does not imply that unprobed third-party providers are healthy.",
        "response_generated_at": datetime.utcnow().isoformat() + "Z",
    }


@router.get("/api/system/deployment-status", summary="Honest deployment status and empirical capabilities")
@router.get("/api/deployment-status")
def get_deployment_status():
    """
    Returns empirical facts about this deployment:
    - Number of investigations completed in database
    - Supported retrieval channels (14-16 total)
    - Registered and healthy domain modules
    - Real deployment identifier (if configured in environment)
    - Distinct response generation vs capability probe timestamps
    """
    try:
        all_claims = db.get_all_claims(limit=500) if hasattr(db, "get_all_claims") else []
        completed_count = sum(1 for c in all_claims if str(c.get("status", "")).lower() == "completed")
        total_claims = len(all_claims)
    except Exception as e:
        logger.debug(f"[DeploymentStatus] Claims count note: {e}")
        completed_count = 0
        total_claims = 0

    from backend.services.agent_reach import agent_reach_service
    channel_names = agent_reach_service.registry.channel_names if hasattr(agent_reach_service, "registry") else [
        "web", "news", "rss", "academic", "twitter", "reddit", "youtube", "bilibili", "tiktok", "instagram", "facebook", "xiaohongshu", "v2ex", "github"
    ]

    deployment_id = os.getenv("DEPLOYMENT_ID") or os.getenv("RENDER_SERVICE_ID") or os.getenv("VERCEL_GIT_COMMIT_SHA") or None
    deployment_id_status = "CONFIGURED" if deployment_id else "UNAVAILABLE"

    from backend.services.agent_reach.native.doctor import native_doctor
    last_probe_ts = getattr(native_doctor, "_last_check_ts", 0.0)
    last_probe_at = datetime.utcfromtimestamp(last_probe_ts).isoformat() + "Z" if last_probe_ts > 0 else None
    last_probe_status = "PROBED" if last_probe_ts > 0 else "NOT_PROBED"

    now_iso = datetime.utcnow().isoformat() + "Z"

    registered_modules = [
        "ClaimIngestionAgent",
        "ResearchAgent",
        "InvestigatorAgent",
        "TrendingAgent",
        "ScoutAgent",
        "BrandShieldAgent",
        "PersonalWatchAgent"
    ]
    registered_count = len(registered_modules)
    healthy_count = 0  # No agent-level execution health probes exist yet.

    return {
        "status": "online",
        "version": __version__,
        "deployment_id": deployment_id,
        "deployment_id_status": deployment_id_status,
        "response_generated_at": now_iso,
        "timestamp": now_iso,  # Preserved for backward compatibility
        "last_capability_probe_at": last_probe_at,
        "last_capability_probe_status": last_probe_status,
        "last_successful_backend_sync_at": None,
        "last_successful_backend_sync_status": "UNAVAILABLE",
        "investigations_completed": completed_count,
        "investigations_stored": total_claims,
        "supported_channels_count": len(channel_names),
        "supported_channel_count": len(channel_names),
        "supported_channels": channel_names,
        "registered_agent_count": registered_count,
        "healthy_agent_count": healthy_count,
        "healthy_agent_count_status": "NOT_PROBED",
        "active_agent_count": None,  # On-demand execution architecture; no static background workers running continuously
        "active_agent_count_status": "NOT_APPLICABLE_ON_DEMAND_EXECUTION",
        "specialized_agents_count": registered_count,
        "specialized_agents": registered_modules,
        "architecture_claims": {
            "registered_modules": f"{registered_count} Specialized Domain Modules",
            "execution_mode": "Deterministic Pipeline + Selective Semantic AI",
            "provenance": "Empirical Multi-Channel Lineage"
        },
        "metrics_policy": "NO_SYNTHETIC_DATA_POLICY_ACTIVE"
    }


@router.get("/api/")
async def api_info():
    """System overview and high-level routing index."""
    return {
        "name": "Aegis Protocol API",
        "version": __version__,
        "architecture": "Deterministic Evidence Pipeline with Selective Semantic AI",
        "documentation": "/docs",
        "redoc": "/redoc",
        "registered_modules": [
            "ClaimIngestionAgent",
            "ResearchAgent",
            "InvestigatorAgent",
            "TrendingAgent",
            "ScoutAgent",
            "BrandShieldAgent",
            "PersonalWatchAgent"
        ],
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
            "telemetry": ["GET /api/system/agents", "GET /api/healthz", "GET /api/system/deployment-status"]
        }
    }


@router.get("/api/media/launch-info", tags=["Media & Teaser"])
async def launch_video_info():
    """Get metadata and resource paths for the official Aegis Protocol launch video."""
    video_path = "docs/showcase/brag.mp4" if os.path.exists("docs/showcase/brag.mp4") else "brag-output/brag.mp4"
    poster_path = "docs/showcase/brag.png" if os.path.exists("docs/showcase/brag.png") else "brag-output/brag.png"
    return {
        "title": "Aegis Protocol — Official Launch Film",
        "duration_seconds": 20,
        "format": "1080p landscape (1920x1080)",
        "interactive_player": "/launch-video",
        "video_path": video_path,
        "poster_path": poster_path,
        "scenes": 4,
        "status": "ready"
    }



@router.get("/api/system/agents", summary="Telemetry & Capability Matrix for All 7 Agents")
async def get_system_agents():
    """
    Returns real-time status, capabilities, models, and diagnostic telemetry
    for all 7 agents in the Aegis Protocol multi-agent architecture.
    """
    payload = {
        "timestamp": datetime.now().isoformat(),
        "total_agents": 7,
        "swarm_status": "ON_DEMAND_NOT_PROBED",
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
                "engine": "Shared Public Evidence Acquisition + Brand Signal Analysis",
                "capabilities": ["counterfeit_signal_analysis", "review_pattern_analysis", "reputational_smear_alerting", "response_recommendations"]
            },
            "personal_watch": {
                "name": "PersonalWatchAgent",
                "role": "VIP Reputation, Deepfake & Impersonation Shield",
                "status": "active",
                "engine": "Public Search Evidence + Identity Signal Analysis",
                "capabilities": ["public_deepfake_claim_analysis", "social_handle_impersonation_signals", "public_exposure_signals", "reputation_threat_scoring"]
            }
        },
        "scraper_fabric": {
            "engine": "AgentReach Zero-Cost Scraper (Panniantong Compatible)",
            "status": "REGISTERED_NOT_PROBED",
            "channels": ["Reddit Discussion Streams", "Twitter/X Targeted Search", "YouTube Video Transcripts", "Google News RSS", "Jina Reader Clean Markdown"]
        }
    }
    for agent in payload["agents"].values():
        agent["status"] = "REGISTERED_ON_DEMAND"
        agent["health_status"] = "NOT_PROBED"
    payload["note"] = "Inventory lists registered functionality, not verified agent or provider health."
    return payload


@router.post("/api/gemini")
@router.post("/.netlify/functions/gemini")
def gemini_proxy(request: GeminiProxyRequest):
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
def get_dashboard_claims(fresh: bool = False):
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
                        verdict = normalize_dashboard_verdict(row.get("verdict"))
                        results.append({
                            "claim":        row.get("claim_text", ""),
                            "verdict":      verdict,
                            "explanation":  row.get("reasoning") or "No investigation reasoning was recorded.",
                            "evidence_url": row.get("source_url") or "",
                            "record_origin": "investigation"
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
                    "verdict":      normalize_dashboard_verdict(item.get("label")),
                    "explanation":  "Historical dataset example; not a live investigation.",
                    "evidence_url": "",
                    "record_origin": "historical_dataset"
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
def dashboard_debug():
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
