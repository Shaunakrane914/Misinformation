"""
FastAPI Backend for Misinformation Detection System

Phase 3: Database integration with Supabase.
All claims and evidence stored in database.
"""

import os
import os
import time
import uuid
from typing import Dict, Optional
from fastapi import FastAPI, BackgroundTasks, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.gzip import GZipMiddleware
from starlette.responses import FileResponse
import asyncio
from fastapi.responses import JSONResponse
import hashlib
from pydantic import BaseModel
import logging
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables from .env file
load_dotenv()

from backend.agents.claim_ingestion_agent import ClaimIngestionAgent
from backend.agents.research_agent import ResearchAgent
from backend.agents.investigator_agent import InvestigatorAgent
from backend.agents.trending_agent import TrendingAgent
from backend.db import database as db
from backend.workers.claim_worker import process_claim
from backend.services.dashboard_loader import load_random_dashboard_claims

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format='ts=%(asctime)s level=%(levelname)s logger=%(name)s msg="%(message)s"',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Misinformation Detection API",
    description="API for detecting and fact-checking misinformation claims",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("ALLOWED_ORIGIN", "*")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=500)

# Lazy-loaded agents (initialized when first needed)
_claim_ingestion_agent = None
_research_agent = None
_investigator_agent = None
_trending_agent = None


def get_claim_ingestion_agent():
    """Lazy-load the ClaimIngestionAgent."""
    global _claim_ingestion_agent
    if _claim_ingestion_agent is None:
        logger.info("[FastAPI] Initializing ClaimIngestionAgent...")
        _claim_ingestion_agent = ClaimIngestionAgent()
    return _claim_ingestion_agent


def get_research_agent():
    """Lazy-load the ResearchAgent."""
    global _research_agent
    if _research_agent is None:
        logger.info("[FastAPI] Initializing ResearchAgent...")
        _research_agent = ResearchAgent()
    return _research_agent


def get_investigator_agent():
    """Lazy-load the InvestigatorAgent."""
    global _investigator_agent
    if _investigator_agent is None:
        logger.info("[FastAPI] Initializing InvestigatorAgent...")
        _investigator_agent = InvestigatorAgent()
    return _investigator_agent


def get_trending_agent():
    """Lazy-load the TrendingAgent used by the Bollywood ingestion API."""
    global _trending_agent
    if _trending_agent is None:
        logger.info("[FastAPI] Initializing TrendingAgent...")
        _trending_agent = TrendingAgent()
    return _trending_agent


logger.info("[FastAPI] Application initialized with Supabase database")


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class ClaimSubmitRequest(BaseModel):
    """Request model for submitting a claim."""
    claim_text: str
    source_url: Optional[str] = None


class ClaimSubmitResponse(BaseModel):
    """Response model for claim submission."""
    claim_id: str
    status: str
    is_new: bool


class TrendingScanRequest(BaseModel):
    """Request body for the Trending Agent scan endpoint."""
    asset_name: str
    identifiers: Optional[Dict] = None


# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.get("/")
async def root():
    """Serve the homepage."""
    return FileResponse("frontend/index.html")


@app.post("/claims/submit", response_model=ClaimSubmitResponse)
async def submit_claim(request: ClaimSubmitRequest, background_tasks: BackgroundTasks):
    """
    Submit a claim for fact-checking.
    
    This endpoint:
    1. Ingests the claim using ClaimIngestionAgent
    2. Checks if claim already exists by hash
    3. If existing, returns existing claim
    4. If new, inserts into database and triggers background processing
    5. Returns claim_id and status immediately
    
    Args:
        request: ClaimSubmitRequest with claim_text and optional source_url
        background_tasks: FastAPI background tasks manager
    
    Returns:
        ClaimSubmitResponse with claim_id, status, and is_new flag
    """
    logger.info(f"[API] POST /claims/submit - Claim: {request.claim_text[:50]}...")
    
    try:
        # Step 1: Run ClaimIngestionAgent to get hash and normalized text
        logger.info(f"[API] Running ClaimIngestionAgent for claim: {request.claim_text[:50]}...")
        claim_ingestion_agent = get_claim_ingestion_agent()
        ingest_result = claim_ingestion_agent.ingest(
            claim_text=request.claim_text,
            source_url=request.source_url
        )
        
        claim_hash = ingest_result["claim_id"]  # This is the SHA256 hash
        normalized_text = ingest_result["normalized_text"]
        
        logger.info(f"[API] Claim hash: {claim_hash}")
        
        # Step 2: Check if claim already exists
        existing_claim = db.get_claim_by_hash(claim_hash)
        
        if existing_claim:
            # Claim already exists
            logger.info(f"[API] Claim already exists with ID: {existing_claim['id']}")
            return ClaimSubmitResponse(
                claim_id=str(existing_claim['id']),
                status=existing_claim['status'],
                is_new=False
            )
        
        # Step 3: Insert new claim into database
        logger.info(f"[API] Inserting new claim into database...")
        inserted_claim = db.insert_claim(
            claim_hash=claim_hash,
            claim_text=request.claim_text,
            normalized_text=normalized_text
        )
        
        claim_id = str(inserted_claim['id'])
        logger.info(f"[API] New claim inserted with ID: {claim_id}")
        
        # Step 4: Trigger background processing
        background_tasks.add_task(process_claim, claim_id)
        logger.info(f"[API] Background processing task added for claim_id: {claim_id}")
        
        # Step 5: Return response
        return ClaimSubmitResponse(
            claim_id=claim_id,
            status="pending",
            is_new=True
        )
        
    except Exception as e:
        logger.error(f"[API] Error submitting claim: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing claim: {str(e)}")


@app.get("/claims/{claim_id}")
async def get_claim_status(claim_id: str):
    """
    Get the status and results of a claim.
    
    Fetches the claim from database and includes associated evidence.
    If the claim doesn't exist, returns a 404 error.
    
    Args:
        claim_id (str): The ID of the claim to retrieve
    
    Returns:
        Full claim data including status, verdict, and evidence list
    """
    logger.info(f"[API] GET /claims/{claim_id}")
    
    try:
        # Fetch claim from database
        claim = db.get_claim_by_id(claim_id)
        
        if not claim:
            logger.warning(f"[API] Claim not found: {claim_id}")
            raise HTTPException(status_code=404, detail=f"Claim not found: {claim_id}")
        
        logger.info(f"[API] Claim found with status: {claim['status']}")
        
        # Fetch associated evidence
        evidence_list = db.get_evidence_by_claim_id(claim_id)
        logger.info(f"[API] Found {len(evidence_list)} evidence items for claim {claim_id}")
        
        # Build response
        response = {
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
        
        logger.info(f"[API] Returning claim data for {claim_id}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[API] Error retrieving claim: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving claim: {str(e)}")


class DefenseRequest(BaseModel):
    """Request body for generating a defense statement."""
    rumor_text: str


@app.post("/api/trending/scan")
async def trending_scan(request: TrendingScanRequest):
    """
    Trigger the Bollywood Trending Agent ingestion pass.

    Returns raw paparazzi + news data + critical alerts.
    """
    logger.info(f"[API] POST /api/trending/scan - asset={request.asset_name}")
    try:
        agent = get_trending_agent()
        result = agent.scan(request.asset_name, request.identifiers)
        
        # Check for critical threats
        from backend.services.alerts import check_critical_threats
        alerts = check_critical_threats(result)
        result["alerts"] = alerts
        
        return result
    except Exception as e:
        logger.error(f"[API] Trending scan failed: {e}")
        raise HTTPException(status_code=500, detail=f"Trending scan failed: {str(e)}")


@app.post("/api/defense/generate")
async def generate_defense_endpoint(request: DefenseRequest):
    """
    Generate a PR defense statement using Gemini.
    """
    logger.info(f"[API] POST /api/defense/generate")
    try:
        from backend.services.intelligence import generate_defense
        statement = generate_defense(request.rumor_text)
        return {"defense_statement": statement}
    except Exception as e:
        logger.error(f"[API] Defense generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Defense generation failed: {str(e)}")


@app.get("/claims")
async def list_all_claims(limit: int = 50, offset: int = 0):
    """
    List all claims in the system (for debugging/testing).
    
    Args:
        limit: Maximum number of claims to return (default 50)
        offset: Number of claims to skip (default 0)
    
    Returns:
        List of claims with pagination info
    """
    logger.info(f"[API] GET /claims - Listing claims (limit={limit}, offset={offset})")
    
    try:
        # Fetch claims from database 
        # Note: You'd need to implement pagination in database.py for this to work fully
        response = db.supabase.table("claims").select("id, claim_text, status, verdict, created_at").range(offset, offset + limit - 1).execute()
        
        claims_list = response.data if response.data else []
        
        logger.info(f"[API] Returning {len(claims_list)} claims")
        
        return {
            "total_claims": len(claims_list),
            "limit": limit,
            "offset": offset,
            "claims": claims_list
        }
        
    except Exception as e:
        logger.error(f"[API] Error listing claims: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error listing claims: {str(e)}")


# ============================================================================
# APPLICATION STARTUP
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Log application startup."""
    logger.info("=" * 80)
    logger.info("[FastAPI] Misinformation Detection API - STARTING")
    logger.info("[FastAPI] Phase 3: Database integration mode")
    logger.info(f"[FastAPI] Supabase URL: {os.getenv('SUPABASE_URL', 'NOT SET')}")
    logger.info("[FastAPI] Agents initialized:")
    logger.info("  - ClaimIngestionAgent: Ready")
    logger.info("  - ResearchAgent: Ready")
    logger.info("  - InvestigatorAgent: Ready")
    logger.info("=" * 80)


@app.on_event("shutdown")
async def shutdown_event():
    """Log application shutdown."""
    logger.info("=" * 80)
    logger.info("[FastAPI] Misinformation Detection API - SHUTTING DOWN")
    logger.info("=" * 80)


if __name__ == "__main__":
    import uvicorn
    
    logger.info("[FastAPI] Starting server on http://0.0.0.0:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)
# Dashboard endpoints

@app.get("/dashboard/claims")
async def get_dashboard_claims(fresh: bool = False):
    logger.info("[API] GET /dashboard/claims - Generating dashboard claims")
    try:
        if fresh:
            claims = load_random_dashboard_claims(n=15)
        else:
            from backend.services.dashboard_loader import get_dashboard_claims_rotating
            logger.info("[API] Using rotating cache for dashboard claims")
            claims = get_dashboard_claims_rotating(n=15, ttl_seconds=int(os.getenv("DASHBOARD_TTL", "300")))
        logger.info(f"[API] Loaded {len(claims)} dashboard claims")
        results = [
            {
                "claim": item.get("claim", ""),
                "verdict": item.get("label", "False"),
                "explanation": "Click 'Show Evidence' for AI-generated explanation.",
                "evidence_url": ""
            }
            for item in claims
        ]
        logger.info(f"[API] Returning {len(results)} dashboard claims")
        # Prevent intermediary caching and expose source for debugging
        sample_id = str(uuid.uuid4())
        first_claim = results[0]["claim"] if results else ""
        checksum = hashlib.sha1("\n".join([r["claim"] for r in results]).encode("utf-8", errors="ignore")).hexdigest()
        logger.info(f"[API] SampleId={sample_id} First='{first_claim[:80]}' Checksum={checksum}")
        headers = {
            "Cache-Control": "no-store, no-cache, max-age=0, must-revalidate",
            "Pragma": "no-cache",
            "X-Dashboard-Source": "rotating",
            "X-Sample-Id": sample_id,
            "X-First-Claim": first_claim[:120],
            "X-Claims-Checksum": checksum
        }
        return JSONResponse(content=results, headers=headers)
    except Exception as e:
        logger.error(f"[API] Error generating dashboard claims: {str(e)}")
        raise HTTPException(status_code=500, detail="Error generating dashboard claims")


@app.get("/dashboard/debug")
async def dashboard_debug():
    try:
        from backend.services.dashboard_loader import get_dashboard_claims_rotating
        claims = get_dashboard_claims_rotating(n=15, ttl_seconds=int(os.getenv("DASHBOARD_TTL", "300")))
        sample_id = str(uuid.uuid4())
        first_claim = claims[0]["claim"] if claims else ""
        checksum = hashlib.sha1("\n".join([r["claim"] for r in claims]).encode("utf-8", errors="ignore")).hexdigest()
        logger.info(f"[DEBUG] SampleId={sample_id} First='{first_claim[:80]}' Checksum={checksum} size={len(claims)}")
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


@app.post("/explain-claim")
async def explain_claim(request: dict):
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
        return {
            "explanation": f"Unable to generate explanation right now.",
            "evidence_url": ""
        }
@app.middleware("http")
async def request_logger(request: Request, call_next):
    rid = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    start = time.perf_counter()
    response = await call_next(request)
    duration = (time.perf_counter() - start) * 1000.0
    logger.info(
        f"[HTTP] rid={rid} method={request.method} path={request.url.path} status={response.status_code} duration_ms={duration:.1f}"
    )
    response.headers["X-Request-ID"] = rid
    return response

# ============================================================================
# WAR ROOM API ENDPOINTS
# ============================================================================

@app.get("/war-room/signals")
async def get_war_room_signals(limit: int = 20):
    """
    Get recent active signals detected by the Scout Agent.
    Returns the last N crash/volatility events.
    """
    logger.info(f"[API] GET /war-room/signals (limit={limit})")
    
    try:
        if db.supabase:
            response = db.supabase.table("active_signals").select("*").order("timestamp", desc=True).limit(limit).execute()
            signals = response.data if response.data else []
            logger.info(f"[API] Returning {len(signals)} active signals")
            return {"signals": signals, "count": len(signals)}
        else:
            # Fallback if no database
            logger.warning("[API] Supabase not configured, returning empty")
            return {"signals": [], "count": 0}
    except Exception as e:
        logger.error(f"[API] Error fetching signals: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching signals: {str(e)}")


@app.get("/feed/live")
async def get_live_feed(limit: int = 10):
    """
    Get recent verified threats (correlated misinformation + crashes).
    This is the main feed for the War Room dashboard.
    """
    logger.info(f"[API] GET /feed/live (limit={limit})")
    
    try:
        if db.supabase:
            response = db.supabase.table("verified_threats").select("*").order("created_at", desc=True).limit(limit).execute()
            threats = response.data if response.data else []
            logger.info(f"[API] Returning {len(threats)} verified threats")
            return {"threats": threats, "count": len(threats)}
        else:
            logger.warning("[API] Supabase not configured, returning empty")
            return {"threats": [], "count": 0}
    except Exception as e:
        logger.error(f"[API] Error fetching live feed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching live feed: {str(e)}")


class DeployResponseRequest(BaseModel):
    event_id: int
    response_type: str  # 'cease_desist', 'official_denial', 'ceo_alert'


@app.post("/deploy-response")
async def deploy_response(request: DeployResponseRequest):
    """
    Deploy a crisis response for a verified threat.
    Records the deployment in deployed_measures table.
    """
    logger.info(f"[API] POST /deploy-response - event_id={request.event_id}, type={request.response_type}")
    
    try:
        if not db.supabase:
            raise HTTPException(status_code=503, detail="Database not configured")
        
        # First, verify the event exists
        event_response = db.supabase.table("verified_threats").select("*").eq("id", request.event_id).execute()
        
        if not event_response.data:
            logger.warning(f"[API] Event {request.event_id} not found")
            raise HTTPException(status_code=404, detail=f"Event {request.event_id} not found")
        
        event = event_response.data[0]
        ticker = event.get("ticker")
        
        # Get current stock price
        from backend.agents.scout_agent import ScoutAgent
        scout = ScoutAgent()
        stock_data = scout.check_stock_impact(ticker)
        current_price = stock_data.get("current_price", 0.0)
        
        # Insert into deployed_measures
        measure_payload = {
            "event_id": request.event_id,
            "measure_type": request.response_type,
            "current_stock_price": current_price,
            "stock_price_at_deployment": event.get("current_price"),
            "metadata": {
                "ticker": ticker,
                "deployed_via": "api"
            }
        }
        
        insert_response = db.supabase.table("deployed_measures").insert(measure_payload).execute()
        
        # Mark response as deployed in verified_threats
        db.supabase.table("verified_threats").update({"response_deployed": True}).eq("id", request.event_id).execute()
        
        logger.info(f"[API] Response deployed successfully: {request.response_type} for event {request.event_id}")
        
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
# TRENDING STOCK NEWS ENDPOINT
# ============================================================================

@app.get("/api/trending-news")
async def get_trending_news():
    """
    Fetch live trending stock market news from Google News RSS.
    Returns latest news for major Indian stocks.
    """
    logger.info("[API] GET /api/trending-news")
    
    try:
        from backend.agents.trending_agent import TrendingAgent
        
        trending = TrendingAgent()
        
        search_queries = [
            "Indian stock market",
            "Reliance Industries",
            "Tata Motors",
            "Infosys",
            "US stock market",
            "Apple",
            "Tesla",
            "Microsoft"
        ]
        
        all_articles = []
        
        for query in search_queries:
            # Fetch news from last 24 hours (1440 minutes)
            articles = trending.fetch_targeted_news(query, window_mins=1440)
            all_articles.extend(articles)
        
        # Remove duplicates based on title
        unique_articles = {article['title']: article for article in all_articles}.values()
        
        # Sort by publication time (newest first) and take top 4
        sorted_articles = sorted(
            unique_articles,
            key=lambda x: x.get('published', ''),
            reverse=True
        )[:4]
        
        # Format for frontend
        news_items = []
        for article in sorted_articles:
            news_items.append({
                'title': article.get('title', 'No title'),
                'link': article.get('link', '#'),
                'time': article.get('age_minutes', 0),
                'source': 'Market News'
            })
        
        logger.info(f"[API] Returning {len(news_items)} trending news articles")
        return {"items": news_items, "count": len(news_items)}
        
    except Exception as e:
        logger.error(f"[API] Error fetching trending news: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch trending news: {str(e)}")


# ============================================================================
# SCOUT AGENT ANALYSIS ENDPOINT
# ============================================================================

class ScoutAnalyzeRequest(BaseModel):
    ticker: str


@app.post("/scout/analyze")
async def analyze_stock_live(request: ScoutAnalyzeRequest):
    """
    Analyze any stock with real-time data and news.
    Returns stock metrics, company news, CEO news, and market analysis.
    """
    logger.info(f"[API] POST /scout/analyze - ticker={request.ticker}")
    
    try:
        from backend.agents.scout_agent import ScoutAgent
        from backend.agents.trending_agent import TrendingAgent
        
        scout = ScoutAgent()
        trending = TrendingAgent()
        
        # Get stock data
        logger.info(f"Fetching stock data for {request.ticker}")
        stock_data = scout.check_stock_impact(request.ticker)
        
        if not stock_data:
            logger.warning(f"No stock data returned for {request.ticker}")
            try:
                url = f"https://yfapi.net/v8/finance/chart/{request.ticker}"
                headers = {'X-API-KEY': os.getenv("YF_API_KEY", ""), 'accept': 'application/json'}
                params = {'range': '5d', 'interval': '1d', 'indicators': 'quote', 'includeTimestamps': 'true'}
                r = requests.get(url, headers=headers, params=params, timeout=10)
                last_price = 0.0
                drop = 0.0
                if r.status_code == 200:
                    d = r.json()
                    rr = d.get('chart', {}).get('result', [])
                    if rr:
                        q = rr[0].get('indicators', {}).get('quote', [])
                        closes = [p for p in (q[0].get('close', []) if q else []) if p is not None]
                        if closes:
                            last_price = float(closes[-1])
                            if len(closes) >= 2:
                                first = float(closes[-2])
                                if first != 0:
                                    drop = ((last_price - first) / first) * 100.0
                stock_data = {
                    "ticker": request.ticker,
                    "current_price": round(last_price, 2),
                    "drop_percent": round(drop, 2),
                    "z_score": 0,
                    "is_crashing": False
                }
            except Exception as e:
                logger.warning(f"Fallback daily close failed: {e}")
                stock_data = {
                    "ticker": request.ticker,
                    "current_price": 0,
                    "drop_percent": 0,
                    "z_score": 0,
                    "is_crashing": False,
                    "error": "Market closed or invalid ticker"
                }
        if not stock_data.get("current_price"):
            try:
                us_ticker = "AAPL"
                us_stock = scout.check_stock_impact(us_ticker)
                if us_stock and us_stock.get("current_price"):
                    stock_data = {
                        "ticker": request.ticker,
                        "current_price": us_stock.get("current_price"),
                        "drop_percent": us_stock.get("drop_percent", 0),
                        "z_score": us_stock.get("z_score", 0),
                        "is_crashing": us_stock.get("is_crashing", False),
                        "fallback_ticker": us_ticker
                    }
            except Exception:
                pass
        
        # Get company name from ticker (fix the extraction)
        # Remove exchange suffix and clean up
        if '.NS' in request.ticker:
            company_name = request.ticker.replace('.NS', '')
        elif '.BO' in request.ticker:
            company_name = request.ticker.replace('.BO', '')
        else:
            company_name = request.ticker
        
        logger.info(f"[DEBUG] Ticker: {request.ticker} → Company: {company_name}")
        
        # Fetch news - use deep_scan mode for general news instead of hunt mode
        logger.info(f"Fetching general news for {company_name}")
        
        # Use deep_scan mode to get general company news
        company_task = {
            'mode': 'deep_scan',
            'ticker': request.ticker,
            'company_name': company_name,
            'search_terms': [company_name],  # Just search for company name
            'time_window_hours': 72  # Last 72 hours
        }
        logger.info(f"[DEBUG] Calling Trending Agent with task: {company_task}")
        company_news_result = trending.process_task(company_task)
        logger.info(f"[DEBUG] Trending Agent returned: {company_news_result}")
        
        # CEO news (extract CEO name from company - simplified)
        ceo_news = []
        
        # Stock analysis news
        analysis_news = []
        
        # Extract articles from company news result
        company_articles = []
        if company_news_result.get('articles'):
            logger.info(f"[DEBUG] Found {len(company_news_result['articles'])} articles")
            for article in company_news_result['articles'][:5]:
                logger.info(f"[DEBUG] Article: {article.get('title', 'No title')}")
                company_articles.append({
                    'title': article.get('title', 'No title'),
                    'source': article.get('source', 'Unknown'),
                    'time': article.get('pub_date', 'Recent')
                })
        else:
            logger.warning(f"[DEBUG] No articles found in result. Keys: {company_news_result.keys()}")
        
        logger.info(f"[DEBUG] Extracted {len(company_articles)} articles for response")
        
        result = {
            "stock": stock_data,
            "news": {
                "company": company_articles,
                "ceo": ceo_news,
                "analysis": analysis_news
            },
            "ticker": request.ticker,
            "analyzed_at": datetime.now().isoformat()
        }
        
        logger.info(f"[API] Scout analysis complete for {request.ticker}")
        return result
        
    except Exception as e:
        logger.error(f"[API] Error in scout analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}


@app.on_event("startup")
async def warm_dashboard_cache():
    try:
        from backend.services.dashboard_loader import get_dashboard_claims_rotating
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, lambda: get_dashboard_claims_rotating(n=15, ttl_seconds=int(os.getenv("DASHBOARD_TTL", "300"))))
        logger.info("[Startup] Dashboard cache warmed")
    except Exception as e:
        logger.warning(f"[Startup] Failed to warm dashboard cache: {e}")


# ============================================================================
# FRONTEND SERVING
# ============================================================================

@app.get("/dashboard")
async def dashboard_page():
    """Serve the main dashboard."""
    return FileResponse("frontend/dashboard.html")

@app.get("/agents")
async def agents_page():
    """Serve the agents page."""
    return FileResponse("frontend/agents.html")

@app.get("/about")
async def about_page():
    """Serve the about page."""
    return FileResponse("frontend/about.html")

@app.get("/submit")
async def submit_page():
    """Serve the submit claim page."""
    return FileResponse("frontend/submit.html")

@app.get("/trending-agent")
async def trending_agent_page():
    """Serve the Trending Agent page."""
    return FileResponse("frontend/trending-agent.html")

@app.get("/scout-agent")
async def scout_agent_page():
    """Serve the Scout Agent page."""
    return FileResponse("frontend/scout-agent.html")

# Serve static assets
@app.get("/dashboard.css")
async def dashboard_css():
    """Serve dashboard CSS."""
    return FileResponse("frontend/dashboard.css")

@app.get("/dashboard.js")
async def dashboard_js():
    """Serve dashboard JS."""
    return FileResponse("frontend/dashboard.js")

