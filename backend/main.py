"""
FastAPI Backend for Aegis Protocol — Misinformation Detection System

v3.0.0 — September 2026
- Removed duplicate route definitions
- Added BrandShield Agent endpoint
- Wired Personal Watch Agent endpoint
- Built-in RSS ingestion loop (15-min interval)
"""

import os
import time
import uuid
import asyncio
import hashlib
import requests
import logging

from typing import Dict, Optional
from datetime import datetime
from fastapi import FastAPI, BackgroundTasks, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.gzip import GZipMiddleware
from starlette.responses import FileResponse
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

# ── Agents & services ────────────────────────────────────────────────────────
from backend.agents.claim_ingestion_agent import ClaimIngestionAgent
from backend.agents.research_agent import ResearchAgent
from backend.agents.investigator_agent import InvestigatorAgent
from backend.agents.trending_agent import TrendingAgent
from backend.db import database as db
from backend.workers.claim_worker import process_claim
from backend.services.dashboard_loader import load_random_dashboard_claims

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format='ts=%(asctime)s level=%(levelname)s logger=%(name)s msg="%(message)s"',
    datefmt='%Y-%m-%d %H:%M:%S',
    encoding='utf-8'
)
logger = logging.getLogger(__name__)

# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Aegis Protocol API",
    description="Multi-agent AI system for real-time misinformation detection and claim verification.",
    version="3.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("ALLOWED_ORIGIN", "*")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=500)

app.mount("/static", StaticFiles(directory="frontend"), name="static")

logger.info("[FastAPI] Aegis Protocol API v3.0.0 initialized")


# ============================================================================
# REQUEST LOGGING MIDDLEWARE
# ============================================================================

@app.middleware("http")
async def request_logger(request: Request, call_next):
    rid = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    start = time.perf_counter()
    response = await call_next(request)
    duration = (time.perf_counter() - start) * 1000.0
    logger.info(
        f"[HTTP] rid={rid} method={request.method} path={request.url.path} "
        f"status={response.status_code} duration_ms={duration:.1f}"
    )
    response.headers["X-Request-ID"] = rid
    return response


# ============================================================================
# LAZY-LOADED AGENT INSTANCES
# ============================================================================

_claim_ingestion_agent = None
_research_agent = None
_investigator_agent = None
_trending_agent = None


def get_claim_ingestion_agent():
    global _claim_ingestion_agent
    if _claim_ingestion_agent is None:
        logger.info("[FastAPI] Initializing ClaimIngestionAgent...")
        _claim_ingestion_agent = ClaimIngestionAgent()
    return _claim_ingestion_agent


def get_research_agent():
    global _research_agent
    if _research_agent is None:
        logger.info("[FastAPI] Initializing ResearchAgent...")
        _research_agent = ResearchAgent()
    return _research_agent


def get_investigator_agent():
    global _investigator_agent
    if _investigator_agent is None:
        logger.info("[FastAPI] Initializing InvestigatorAgent...")
        _investigator_agent = InvestigatorAgent()
    return _investigator_agent


def get_trending_agent():
    global _trending_agent
    if _trending_agent is None:
        logger.info("[FastAPI] Initializing TrendingAgent...")
        _trending_agent = TrendingAgent()
    return _trending_agent


# ============================================================================
# REQUEST / RESPONSE MODELS
# ============================================================================

class ClaimSubmitRequest(BaseModel):
    claim_text: str
    source_url: Optional[str] = None


class ClaimSubmitResponse(BaseModel):
    claim_id: str
    status: str
    is_new: bool


class TrendingScanRequest(BaseModel):
    asset_name: str
    identifiers: Optional[Dict] = None


class DefenseRequest(BaseModel):
    rumor_text: str


class ScoutAnalyzeRequest(BaseModel):
    ticker: str


class PersonalScanRequest(BaseModel):
    name: str
    official_handles: Optional[Dict[str, str]] = None
    phone_number: Optional[str] = None


class BrandShieldScanRequest(BaseModel):
    brand_name: str


class DeployResponseRequest(BaseModel):
    event_id: int
    response_type: str  # 'cease_desist', 'official_denial', 'ceo_alert'


# ============================================================================
# STARTUP & SHUTDOWN
# ============================================================================

@app.on_event("startup")
async def startup_event():
    logger.info("=" * 80)
    logger.info("[FastAPI] Aegis Protocol API v3.0.0 — STARTING")
    logger.info(f"[FastAPI] Supabase URL: {os.getenv('SUPABASE_URL', 'NOT SET')}")
    logger.info("[FastAPI] Agents: ClaimIngestion | Research | Investigator | Trending")
    logger.info("=" * 80)

    # Warm dashboard cache
    try:
        from backend.services.dashboard_loader import get_dashboard_claims_rotating
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: get_dashboard_claims_rotating(
                n=15, ttl_seconds=int(os.getenv("DASHBOARD_TTL", "300"))
            )
        )
        logger.info("[Startup] Dashboard cache warmed")
    except Exception as e:
        logger.warning(f"[Startup] Failed to warm dashboard cache: {e}")

    # Start RSS ingestion background loop
    if os.getenv("RSS_INGESTION_ENABLED", "true").lower() != "false":
        from backend.services.rss_ingestion import rss_ingestion_loop
        asyncio.create_task(rss_ingestion_loop())
        logger.info("[FastAPI] RSS ingestion loop scheduled (15 min interval)")


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("=" * 80)
    logger.info("[FastAPI] Aegis Protocol API — SHUTTING DOWN")
    logger.info("=" * 80)


# ============================================================================
# HEALTH & INFO
# ============================================================================

@app.get("/")
@app.get("/index.html")
async def root():
    """Serve the homepage."""
    return FileResponse("frontend/index.html")


@app.get("/healthz")
@app.get("/api/healthz")
async def healthz():
    return {"status": "ok", "version": "3.0.0", "timestamp": datetime.now().isoformat()}


@app.get("/api/")
async def api_info():
    return {
        "name": "Aegis Protocol API",
        "version": "3.0.0",
        "agents": ["ClaimIngestion", "Research", "Investigator", "Trending", "Scout", "BrandShield", "PersonalWatch"],
        "endpoints": {
            "claims": ["/api/claims/submit", "/api/claims/{claim_id}", "/api/claims"],
            "dashboard": ["/api/dashboard/claims", "/api/dashboard/debug"],
            "agents": ["/api/trending/scan", "/api/scout/analyze", "/api/brandshield/scan", "/api/personal/scan"],
            "war_room": ["/api/war-room/signals", "/api/feed/live", "/api/deploy-response"],
        }
    }


# ============================================================================
# CLAIMS MANAGEMENT
# ============================================================================

@app.post("/api/claims/submit", response_model=ClaimSubmitResponse)
@app.post("/api/ingest", response_model=ClaimSubmitResponse)
@app.post("/api/submit", response_model=ClaimSubmitResponse)
async def submit_claim(request: ClaimSubmitRequest, background_tasks: BackgroundTasks):
    """
    Submit a claim for fact-checking.

    1. Ingests and normalizes the claim via ClaimIngestionAgent
    2. Checks for duplicate by hash
    3. Inserts new claims into Supabase and triggers background processing
    4. Returns claim_id and status immediately
    """
    logger.info(f"[API] POST /claims/submit - Claim: {request.claim_text[:50]}...")

    try:
        claim_ingestion_agent = get_claim_ingestion_agent()
        ingest_result = claim_ingestion_agent.ingest(
            claim_text=request.claim_text,
            source_url=request.source_url
        )

        claim_hash = ingest_result["claim_id"]
        normalized_text = ingest_result["normalized_text"]
        logger.info(f"[API] Claim hash: {claim_hash}")

        existing_claim = db.get_claim_by_hash(claim_hash)
        if existing_claim:
            logger.info(f"[API] Claim already exists with ID: {existing_claim['id']}")
            return ClaimSubmitResponse(
                claim_id=str(existing_claim['id']),
                status=existing_claim['status'],
                is_new=False
            )

        inserted_claim = db.insert_claim(
            claim_hash=claim_hash,
            claim_text=request.claim_text,
            normalized_text=normalized_text
        )
        claim_id = str(inserted_claim['id'])
        logger.info(f"[API] New claim inserted with ID: {claim_id}")

        background_tasks.add_task(process_claim, claim_id)
        return ClaimSubmitResponse(claim_id=claim_id, status="pending", is_new=True)

    except Exception as e:
        logger.error(f"[API] Error submitting claim: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing claim: {str(e)}")


@app.get("/api/claims/{claim_id}")
async def get_claim_status(claim_id: str):
    """Get status and results of a claim by ID."""
    logger.info(f"[API] GET /claims/{claim_id}")
    try:
        claim = db.get_claim_by_id(claim_id)
        if not claim:
            raise HTTPException(status_code=404, detail=f"Claim not found: {claim_id}")

        evidence_list = db.get_evidence_by_claim_id(claim_id)
        return {
            "claim_id": claim_id,
            "claim_hash": claim.get("claim_hash"),
            "claim_text": claim.get("claim_text"),
            "normalized_text": claim.get("normalized_text"),
            "status": claim.get("status"),
            "verdict": claim.get("verdict"),
            "confidence": claim.get("confidence"),
            "severity": claim.get("severity"),
            "reasoning": claim.get("reasoning"),
            "evidence": evidence_list,
            "created_at": claim.get("created_at"),
            "updated_at": claim.get("updated_at")
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[API] Error retrieving claim: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving claim: {str(e)}")


@app.get("/api/claims")
async def list_all_claims(limit: int = 50, offset: int = 0):
    """List all claims in the system with pagination."""
    logger.info(f"[API] GET /claims - limit={limit}, offset={offset}")
    try:
        response = db.supabase.table("claims") \
            .select("id, claim_text, status, verdict, created_at") \
            .range(offset, offset + limit - 1) \
            .execute()
        claims_list = response.data if response.data else []
        return {"total_claims": len(claims_list), "limit": limit, "offset": offset, "claims": claims_list}
    except Exception as e:
        logger.error(f"[API] Error listing claims: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error listing claims: {str(e)}")


# ============================================================================
# DASHBOARD
# ============================================================================

@app.get("/api/dashboard/claims")
@app.get("/dashboard/claims")
async def get_dashboard_claims(fresh: bool = False):
    """
    Get 15 claims for the live dashboard.
    Priority: real verified Supabase claims first, topped up with WELFake dataset.
    """
    logger.info("[API] GET /dashboard/claims")
    try:
        results = []

        # Step 1: Pull real verified claims from Supabase
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

        # Step 2: Top up with WELFake dataset if fewer than 15 real claims
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
            logger.info(f"[API] Topped up with {needed} dataset claims (total={len(results)})")

        sample_id = str(uuid.uuid4())
        first_claim = results[0]["claim"] if results else ""
        checksum = hashlib.sha1(
            "\n".join([r["claim"] for r in results]).encode("utf-8", errors="ignore")
        ).hexdigest()
        safe_first = first_claim[:80].encode('ascii', 'replace').decode('ascii')
        logger.info(f"[API] SampleId={sample_id} First='{safe_first}' Checksum={checksum}")

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


@app.get("/api/dashboard/debug")
@app.get("/dashboard/debug")
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


@app.post("/api/explain-claim")
@app.post("/explain-claim")
async def explain_claim(request: dict):
    """Generate an AI explanation for a dashboard claim."""
    claim_text = request.get("claim", "")
    verdict = request.get("verdict", "False")
    logger.info(f"[API] POST /explain-claim - Claim: {claim_text[:50]} (verdict={verdict})")
    try:
        agent = get_research_agent()
        result = await agent.generate_dashboard_explanation(claim_text, verdict)
        return {
            "explanation": result.get("explanation", "Explanation unavailable."),
            "evidence_url": result.get("evidence_url", "")
        }
    except Exception as e:
        logger.error(f"[API] Error generating explanation: {str(e)}")
        return {"explanation": "Unable to generate explanation right now.", "evidence_url": ""}


# ============================================================================
# TRENDING AGENT
# ============================================================================

@app.post("/api/trending/scan")
async def trending_scan(request: TrendingScanRequest):
    """Trigger the Trending Agent ingestion pass for an asset/celebrity."""
    logger.info(f"[API] POST /api/trending/scan - asset={request.asset_name}")
    try:
        agent = get_trending_agent()
        result = agent.scan(request.asset_name, request.identifiers)
        from backend.services.alerts import check_critical_threats
        result["alerts"] = check_critical_threats(result)
        return result
    except Exception as e:
        logger.error(f"[API] Trending scan failed: {e}")
        raise HTTPException(status_code=500, detail=f"Trending scan failed: {str(e)}")


@app.post("/api/defense/generate")
async def generate_defense_endpoint(request: DefenseRequest):
    """Generate a PR defense statement using Gemini."""
    logger.info("[API] POST /api/defense/generate")
    try:
        from backend.services.intelligence import generate_defense
        statement = generate_defense(request.rumor_text)
        return {"defense_statement": statement}
    except Exception as e:
        logger.error(f"[API] Defense generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Defense generation failed: {str(e)}")


@app.get("/api/trending-news")
async def get_trending_news():
    """Fetch live trending stock market news from Google News RSS."""
    logger.info("[API] GET /api/trending-news")
    try:
        trending = TrendingAgent()
        search_queries = [
            "Indian stock market", "Reliance Industries", "Tata Motors", "Infosys",
            "US stock market", "Apple", "Tesla", "Microsoft"
        ]
        all_articles = []
        for query in search_queries:
            articles = trending.fetch_targeted_news(query, window_mins=1440)
            all_articles.extend(articles)

        unique_articles = {a['title']: a for a in all_articles}.values()
        sorted_articles = sorted(unique_articles, key=lambda x: x.get('published', ''), reverse=True)[:4]

        news_items = [{
            'title': a.get('title', 'No title'),
            'link': a.get('link', '#'),
            'time': a.get('age_minutes', 0),
            'source': 'Market News'
        } for a in sorted_articles]

        logger.info(f"[API] Returning {len(news_items)} trending news articles")
        return {"items": news_items, "count": len(news_items)}
    except Exception as e:
        logger.error(f"[API] Error fetching trending news: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch trending news: {str(e)}")


# ============================================================================
# SCOUT AGENT
# ============================================================================

@app.post("/api/scout/analyze")
@app.post("/scout/analyze")
async def analyze_stock_live(request: ScoutAnalyzeRequest):
    """
    Analyze a stock ticker with real-time data and news.
    Returns stock metrics, company news, and AI market analysis.
    """
    logger.info(f"[API] POST /api/scout/analyze - ticker={request.ticker}")
    try:
        from backend.agents.scout_agent import ScoutAgent

        scout = ScoutAgent()
        trending = TrendingAgent()

        stock_data = scout.check_stock_impact(request.ticker)

        if not stock_data or not stock_data.get("current_price"):
            try:
                url = f"https://yfapi.net/v8/finance/chart/{request.ticker}"
                headers = {'X-API-KEY': os.getenv("YF_API_KEY", ""), 'accept': 'application/json'}
                params = {'range': '5d', 'interval': '1d', 'indicators': 'quote', 'includeTimestamps': 'true'}
                r = requests.get(url, headers=headers, params=params, timeout=10)
                last_price, drop = 0.0, 0.0
                if r.status_code == 200:
                    d = r.json()
                    rr = d.get('chart', {}).get('result', [])
                    if rr:
                        q = rr[0].get('indicators', {}).get('quote', [])
                        closes = [p for p in (q[0].get('close', []) if q else []) if p is not None]
                        if closes:
                            last_price = float(closes[-1])
                            if len(closes) >= 2 and float(closes[-2]) != 0:
                                drop = ((last_price - float(closes[-2])) / float(closes[-2])) * 100.0
                stock_data = {
                    "ticker": request.ticker, "current_price": round(last_price, 2),
                    "drop_percent": round(drop, 2), "z_score": 0, "is_crashing": False
                }
            except Exception as e:
                logger.warning(f"Fallback daily close failed: {e}")
                stock_data = {
                    "ticker": request.ticker, "current_price": 0, "drop_percent": 0,
                    "z_score": 0, "is_crashing": False, "error": "Market closed or invalid ticker"
                }

        # Extract clean company name
        company_name = request.ticker.replace('.NS', '').replace('.BO', '')

        company_task = {
            'mode': 'deep_scan',
            'ticker': request.ticker,
            'company_name': company_name,
            'search_terms': [company_name],
            'time_window_hours': 72
        }
        company_news_result = trending.process_task(company_task)

        company_articles = []
        for article in (company_news_result.get('articles') or [])[:5]:
            company_articles.append({
                'title': article.get('title', 'No title'),
                'source': article.get('source', 'Unknown'),
                'time': article.get('pub_date', 'Recent')
            })

        return {
            "stock": stock_data,
            "news": {"company": company_articles, "ceo": [], "analysis": []},
            "ticker": request.ticker,
            "analyzed_at": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"[API] Error in scout analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


# ============================================================================
# PERSONAL WATCH AGENT
# ============================================================================

@app.post("/api/personal/scan")
@app.post("/api/personal-watch/scan")
async def personal_watch_scan(request: PersonalScanRequest):
    """
    Run a Personal Watch scan for a public figure or individual.
    Searches web and social media for reputation threats, defamation, and fake content.
    """
    logger.info(f"[API] POST /api/personal/scan - VIP: {request.name}")
    try:
        from backend.agents.personal_agent import process_personal_watch
        vip_profile = {
            "name": request.name,
            "official_handles": request.official_handles or {},
            "phone_number": request.phone_number
        }
        results = process_personal_watch(vip_profile)
        logger.info(
            f"[API] Scan complete: {results.get('total_mentions', 0)} mentions, "
            f"{results.get('high_risk_count', 0)} high-risk"
        )
        return results
    except Exception as e:
        logger.error(f"[API] Personal Watch scan failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Scan failed: {str(e)}")


# ============================================================================
# BRANDSHIELD AGENT
# ============================================================================

@app.post("/api/brandshield/scan")
async def brandshield_scan(request: BrandShieldScanRequest):
    """
    Run a BrandShield scan for a brand or product.
    Detects fake reviews, counterfeit listings, and reputation attacks across
    Amazon, Flipkart, Trustpilot, Reddit, and Google Reviews using AI analysis.
    """
    logger.info(f"[API] POST /api/brandshield/scan - brand={request.brand_name}")
    try:
        from backend.agents.brandshield_agent import BrandShieldAgent
        agent = BrandShieldAgent()
        results = agent.scan(request.brand_name)
        logger.info(
            f"[API] BrandShield scan complete: {results.get('total_findings', 0)} findings, "
            f"{results.get('threat_count', 0)} threats"
        )
        return results
    except Exception as e:
        logger.error(f"[API] BrandShield scan failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"BrandShield scan failed: {str(e)}")


# ============================================================================
# WAR ROOM
# ============================================================================

@app.get("/api/war-room/signals")
@app.get("/war-room/signals")
async def get_war_room_signals(limit: int = 20):
    """Get recent active signals detected by the Scout Agent."""
    logger.info(f"[API] GET /war-room/signals (limit={limit})")
    try:
        if db.supabase:
            response = db.supabase.table("active_signals") \
                .select("*").order("timestamp", desc=True).limit(limit).execute()
            signals = response.data if response.data else []
            return {"signals": signals, "count": len(signals)}
        return {"signals": [], "count": 0}
    except Exception as e:
        logger.error(f"[API] Error fetching signals: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching signals: {str(e)}")


@app.get("/api/feed/live")
@app.get("/feed/live")
async def get_live_feed(limit: int = 10):
    """Get recent verified threats (correlated misinformation + crashes)."""
    logger.info(f"[API] GET /feed/live (limit={limit})")
    try:
        if db.supabase:
            response = db.supabase.table("verified_threats") \
                .select("*").order("created_at", desc=True).limit(limit).execute()
            threats = response.data if response.data else []
            return {"threats": threats, "count": len(threats)}
        return {"threats": [], "count": 0}
    except Exception as e:
        logger.error(f"[API] Error fetching live feed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching live feed: {str(e)}")


@app.post("/api/deploy-response")
@app.post("/deploy-response")
async def deploy_response(request: DeployResponseRequest):
    """Deploy a crisis response measure for a verified threat."""
    logger.info(f"[API] POST /deploy-response - event_id={request.event_id}, type={request.response_type}")
    try:
        if not db.supabase:
            raise HTTPException(status_code=503, detail="Database not configured")

        event_response = db.supabase.table("verified_threats").select("*").eq("id", request.event_id).execute()
        if not event_response.data:
            raise HTTPException(status_code=404, detail=f"Event {request.event_id} not found")

        event = event_response.data[0]
        ticker = event.get("ticker")

        from backend.agents.scout_agent import ScoutAgent
        scout = ScoutAgent()
        stock_data = scout.check_stock_impact(ticker)
        current_price = stock_data.get("current_price", 0.0)

        measure_payload = {
            "event_id": request.event_id,
            "measure_type": request.response_type,
            "current_stock_price": current_price,
            "stock_price_at_deployment": event.get("current_price"),
            "metadata": {"ticker": ticker, "deployed_via": "api"}
        }
        insert_response = db.supabase.table("deployed_measures").insert(measure_payload).execute()
        db.supabase.table("verified_threats").update({"response_deployed": True}).eq("id", request.event_id).execute()

        logger.info(f"[API] Response deployed: {request.response_type} for event {request.event_id}")
        return {
            "status": "success",
            "event_id": request.event_id,
            "response_type": request.response_type,
            "current_stock_price": current_price,
            "measure_id": insert_response.data[0]["id"] if insert_response.data else None
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[API] Error deploying response: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error deploying response: {str(e)}")


# ============================================================================
# FRONTEND PAGE ROUTES
# ============================================================================

@app.get("/dashboard")
@app.get("/dashboard.html")
async def dashboard_page():
    return FileResponse("frontend/dashboard.html")


@app.get("/agents")
@app.get("/agents.html")
async def agents_page():
    return FileResponse("frontend/agents.html")


@app.get("/about")
@app.get("/about.html")
async def about_page():
    return FileResponse("frontend/about.html")


@app.get("/submit")
@app.get("/submit.html")
async def submit_page():
    return FileResponse("frontend/submit.html")


@app.get("/status")
@app.get("/status.html")
async def status_page():
    return FileResponse("frontend/status.html")


@app.get("/changelog")
@app.get("/changelog.html")
async def changelog_page():
    return FileResponse("frontend/changelog.html")


@app.get("/trending-agent")
@app.get("/trending-agent.html")
async def trending_agent_page():
    return FileResponse("frontend/trending-agent.html")


@app.get("/scout-agent")
@app.get("/scout-agent.html")
async def scout_agent_page():
    return FileResponse("frontend/scout-agent.html")


@app.get("/personal-watch-agent")
@app.get("/personal-watch-agent.html")
async def personal_watch_agent_page():
    return FileResponse("frontend/personal-watch-agent.html")


@app.get("/brandshield-agent")
@app.get("/brandshield-agent.html")
async def brandshield_agent_page():
    return FileResponse("frontend/brandshield-agent.html")


@app.get("/favicon.ico")
async def favicon():
    if os.path.exists("frontend/favicon.ico"):
        return FileResponse("frontend/favicon.ico")
    return JSONResponse({"status": "no favicon"}, status_code=404)


@app.get("/dashboard.css")
async def dashboard_css():
    return FileResponse("frontend/dashboard.css")


@app.get("/dashboard.js")
async def dashboard_js():
    return FileResponse("frontend/dashboard.js")


if __name__ == "__main__":
    import uvicorn
    logger.info("[FastAPI] Starting server on http://0.0.0.0:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)
