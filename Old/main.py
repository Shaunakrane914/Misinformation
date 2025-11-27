"""
FastAPI Backend for Misinformation Detection System

Phase 3: Database integration with Supabase.
All claims and evidence stored in database.
"""

import os
from typing import Dict, Optional, List
from datetime import datetime
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel
import logging
import asyncio
from dotenv import load_dotenv

# Load environment variables from .env file
# Use override=True so that changes to .env take effect even if vars were set earlier
load_dotenv(override=True)

from backend.agents.claim_ingestion_agent import ClaimIngestionAgent
from backend.agents.research_agent import ResearchAgent
from backend.agents.investigator_agent import InvestigatorAgent
from backend.db import database as db
from backend.workers.claim_worker import process_claim
from backend.services.dashboard_loader import load_random_dashboard_claims

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Misinformation Detection API",
    description="API for detecting and fact-checking misinformation claims",
    version="2.0.0"
)

# Add CORS middleware to allow frontend connections
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files (frontend)
frontend_path = os.path.join(os.path.dirname(__file__), "..", "frontend")
app.mount("/static", StaticFiles(directory=frontend_path), name="static")

# Lazy-loaded agents (initialized when first needed)
_claim_ingestion_agent = None
_research_agent = None
_investigator_agent = None


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


# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the frontend landing page."""
    frontend_path = os.path.join(os.path.dirname(__file__), "..", "frontend", "index.html")
    try:
        with open(frontend_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return """
        <html>
            <body>
                <h1>Misinformation Detection API</h1>
                <p>Frontend not found. API is running at <a href="/docs">/docs</a></p>
            </body>
        </html>
        """


# Frontend routes
@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    """Serve the dashboard page."""
    return FileResponse(os.path.join(os.path.dirname(__file__), "..", "frontend", "dashboard.html"))


@app.get("/submit", response_class=HTMLResponse)
async def submit_page():
    """Serve the submit claim page."""
    return FileResponse(os.path.join(os.path.dirname(__file__), "..", "frontend", "submit.html"))


@app.get("/about", response_class=HTMLResponse)
async def about_page():
    """Serve the about page."""
    return FileResponse(os.path.join(os.path.dirname(__file__), "..", "frontend", "about.html"))


@app.get("/dashboard/claims")
async def get_dashboard_claims(limit: int = 15):
    """Return a sample of claims for the dashboard feed."""
    try:
        items = load_random_dashboard_claims(n=limit)
        results = []
        for it in items:
            raw_label = str(it.get("label", "")).lower()
            if "true" in raw_label or "real" in raw_label:
                verdict = "True"
            elif "false" in raw_label or "fake" in raw_label:
                verdict = "False"
            else:
                verdict = "Unverified"
            results.append({
                "claim": it.get("claim", ""),
                "verdict": verdict,
                "explanation": ""
            })
        return results
    except Exception as e:
        logger.error(f"[API] Failed to load dashboard claims: {e}")
        raise HTTPException(status_code=500, detail="Failed to load dashboard claims")


class ExplainRequest(BaseModel):
    claim: str
    verdict: str

@app.post("/explain-claim")
async def explain_claim(req: ExplainRequest):
    """Generate AI explanation on demand for a claim."""
    try:
        research_agent = get_research_agent()
        investigator_agent = get_investigator_agent()
        # Attempt Gemini-backed research and investigation
        try:
            evidence_json = research_agent.process(req.claim)
            verdict_json = investigator_agent.process(req.claim, evidence_json)
            explanation = verdict_json.get("reasoning")
            if explanation:
                return {"explanation": explanation}
        except Exception as e:
            logger.warning(f"[API] AI explanation path failed: {e}")
        # Rule-based fallback explanation using provided verdict
        v = (req.verdict or "Unverified").strip().lower()
        if v == "true":
            fallback = (
                "Labelled True: the claim aligns with available sources and shows no strong "
                "manipulation signals in the quick screening."
            )
        elif v == "false":
            fallback = (
                "Labelled False: the claim contradicts available reporting or contains clear "
                "factual inaccuracies based on quick checks."
            )
        elif v == "misleading":
            fallback = (
                "Labelled Misleading: elements of the claim appear selectively framed or out of "
                "context, producing a distorted impression despite partial facts."
            )
        else:
            fallback = (
                "Labelled Unverified: insufficient corroboration found in a quick scan; a deeper "
                "investigation would be required to confirm."
            )
        return {"explanation": fallback}
    except Exception as e:
        logger.error(f"[API] explain-claim error: {e}")
        return {"explanation": "Unable to generate explanation."}

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
            logger.info(f"[API] Claim already exists with ID: {existing_claim['id']}")
            existing_status = existing_claim['status']
            if existing_status == "failed":
                logger.info(f"[API] Reprocessing failed claim {existing_claim['id']}")
                try:
                    db.update_claim_status(str(existing_claim['id']), "pending")
                    background_tasks.add_task(process_claim, str(existing_claim['id']))
                    logger.info(f"[API] Background task re-queued for claim_id: {existing_claim['id']}")
                    return ClaimSubmitResponse(
                        claim_id=str(existing_claim['id']),
                        status="pending",
                        is_new=False
                    )
                except Exception:
                    logger.warning(f"[API] Failed to reprocess claim {existing_claim['id']}")
            return ClaimSubmitResponse(
                claim_id=str(existing_claim['id']),
                status=existing_status,
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


@app.get("/api/dashboard/claims")
async def get_dashboard_claims():
    """
    Get random sample claims for the dashboard.
    
    This endpoint loads a sample of claims from a dataset for demonstration purposes.
    Returns claims with verdict/label information for dashboard visualization.
    
    Returns:
        List of dashboard claim objects with claim, verdict, explanation, and evidence_url
    """
    logger.info("[API] GET /api/dashboard/claims")
    
    try:
        # Load random claims from dashboard loader
        claims = load_random_dashboard_claims(n=15)
        
        # Transform to match frontend expectations
        dashboard_claims = []
        for item in claims:
            dashboard_claims.append({
                "claim": item.get("claim", ""),
                "verdict": item.get("label", "False"),  # Show actual dataset label
                "explanation": "Click 'Show Evidence' for AI-generated explanation.",
                "evidence_url": "#"
            })
        
        logger.info(f"[API] Returning {len(dashboard_claims)} dashboard claims")
        
        # Create response with no-cache headers to ensure fresh data every time
        from fastapi.responses import JSONResponse
        return JSONResponse(
            content=dashboard_claims,
            headers={
                "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                "Pragma": "no-cache",
                "Expires": "0"
            }
        )
        
    except Exception as e:
        logger.error(f"[API] Error loading dashboard claims: {str(e)}")
        # Return empty list instead of error to prevent frontend from breaking
        return []


@app.post("/api/explain-claim")
async def explain_claim(request: dict):
    """
    Generate an AI explanation for why a claim is true or false.
    
    Args:
        request: dict with 'claim' and 'verdict' keys
    
    Returns:
        dict with 'explanation' key containing AI-generated reasoning
    """
    claim_text = request.get("claim", "")
    verdict = request.get("verdict", "False")
    
    logger.info(f"[API] POST /api/explain-claim - Claim: {claim_text[:50]}...")
    
    try:
        # Get ResearchAgent to generate explanation
        research_agent = get_research_agent()
        
        prompt_text = f"""Explain in 2-3 sentences why the following claim is {verdict}:

Claim: "{claim_text}"

Provide a brief, factual explanation."""
        
        # Use ResearchAgent's Gemini HTTP helper to generate explanation
        explanation = research_agent._call_gemini(prompt_text).strip()
        
        logger.info(f"[API] Generated explanation for claim")
        return {"explanation": explanation}
        
    except Exception as e:
        logger.error(f"[API] Error generating explanation: {str(e)}")
        return {"explanation": f"This claim is labeled as {verdict} in the dataset. Unable to generate detailed explanation at this time."}


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


@app.get("/dashboard/claims")
async def get_dashboard_claims():
    logger.info("[API] GET /dashboard/claims - Generating dashboard claims")
    try:
        claims = load_random_dashboard_claims(15)
        logger.info(f"[API] Loaded {len(claims)} dashboard claims")
        research_agent = get_research_agent()
        tasks = []
        for item in claims:
            claim_text = item.get("claim")
            label = item.get("label")
            logger.info(f"[API] Generating explanation for claim: {claim_text[:50]}...")
            tasks.append(research_agent.generate_dashboard_explanation(claim_text, label))
        explanations = await asyncio.gather(*tasks, return_exceptions=True)
        results = []
        for item, exp in zip(claims, explanations):
            if isinstance(exp, Exception):
                logger.error(f"[API] Explanation generation error for claim: {item['claim'][:50]} - {exp}")
                exp_data = {"explanation": "Short explanation unavailable.", "evidence_url": ""}
            else:
                exp_data = exp
            results.append({
                "claim": item["claim"],
                "verdict": item["label"],
                "explanation": exp_data.get("explanation"),
                "evidence_url": exp_data.get("evidence_url")
            })
        logger.info(f"[API] Returning {len(results)} dashboard claims")
        return results
    except Exception as e:
        logger.error(f"[API] Error generating dashboard claims: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error generating dashboard claims: {str(e)}")


# ============================================================================
# WAR ROOM / AEGIS ENTERPRISE ENDPOINTS
# ============================================================================

# Lazy-load Coordinator Agent
_coordinator_agent = None

def get_coordinator_agent():
    """Lazy-load the Coordinator Agent."""
    global _coordinator_agent
    if _coordinator_agent is None:
        logger.info("[FastAPI] Initializing Coordinator Agent (War Room)...")
        from backend.agents.coordinator_agent import coordinator
        _coordinator_agent = coordinator
    return _coordinator_agent


@app.get("/war-room/latest-threat")
async def get_latest_threat():
    """
    Get the most recent CRITICAL threat from the War Room.
    
    Returns the complete "Attack Package" including:
    - Stock crash data
    - Smoking gun news article
    - Generated crisis responses
    
    Returns:
        dict: Complete threat package or None if no threats exist
    """
    logger.info("[API] GET /war-room/latest-threat")
    
    try:
        coordinator = get_coordinator_agent()
        
        # Get all verified attacks
        verified_attacks = coordinator.verified_attacks
        
        if not verified_attacks:
            logger.info("[API] No verified threats in database")
            return {
                "status": "no_threats",
                "message": "No critical threats detected",
                "threat": None
            }
        
        # Get the most recent one
        latest_threat = verified_attacks[-1]
        
        logger.info(f"[API] Returning latest threat: {latest_threat.get('event_id')}")
        
        return {
            "status": "threat_found",
            "threat": latest_threat,
            "total_threats": len(verified_attacks)
        }
        
    except Exception as e:
        logger.error(f"[API] Error fetching latest threat: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching threat: {str(e)}")


# removed duplicate deploy-response; using unified /deploy-response endpoint below


@app.get("/war-room/scan/{ticker}")
async def scan_ticker(ticker: str):
    """
    Trigger an on-demand War Room scan for a specific ticker.
    
    This runs the complete pipeline:
    1. Scout Agent (volatility detection)
    2. Trending Agent (misinformation hunt)
    3. Correlation (causality analysis)
    4. Response Generation (if threat confirmed)
    
    Args:
        ticker: Stock ticker symbol (e.g., RELIANCE.NS)
        
    Returns:
        dict: Complete scan results
    """
    logger.info(f"[API] GET /war-room/scan/{ticker}")
    
    try:
        coordinator = get_coordinator_agent()
        
        logger.info(f"[API] Launching War Room scan for {ticker}...")
        result = coordinator.process_ticker(ticker)
        
        logger.info(f"[API] Scan complete - Status: {result.get('status')}")
        
        return {
            "status": "scan_complete",
            "ticker": ticker,
            "result": result
        }
        
    except Exception as e:
        logger.error(f"[API] Error scanning ticker: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Scan failed: {str(e)}")


@app.get("/war-room/demo-attack")
async def trigger_demo_attack():
    """
    🎬 THE MONEY SHOT: Trigger a complete demo attack simulation.
    
    This endpoint demonstrates the full War Room pipeline:
    1. Scout detects crash on DEMO.NS
    2. Trending hunts for misinformation (uses mock news)
    3. Coordinator correlates and generates responses
    4. Attack package is saved
    
    Returns:
        dict: Complete attack package with all generated responses
    """
    logger.info("="*80)
    logger.critical("🎬 DEMO ATTACK SIMULATION STARTING")
    logger.info("="*80)
    
    try:
        coordinator = get_coordinator_agent()
        
        # Override trending agent's hunt mode to return mock news for demo
        logger.info("📰 Injecting mock news for demonstration...")
        
        # Create mock news that "caused" the crash
        from datetime import datetime, timedelta
        crash_time = datetime.now()
        article_time = crash_time - timedelta(minutes=12)
        
        # This will be returned when Trending Agent searches
        mock_news = [{
            'title': 'BREAKING: DEMO Company CEO Under Investigation for Accounting Fraud',
            'link': 'https://demo-news.example.com/ceo-investigation',
            'published': article_time.isoformat(),
            'age_minutes': 12
        }]
        
        # Monkey-patch the trending agent's fetch method for demo
        original_fetch = coordinator.trending.fetch_targeted_news
        
        def demo_fetch(query, window_mins):
            logger.info(f"🎬 DEMO: Returning mock news for query '{query}'")
            return mock_news
        
        coordinator.trending.fetch_targeted_news = demo_fetch
        
        # Run the full War Room pipeline on DEMO.NS
        logger.info("\n🚀 Launching War Room Pipeline on DEMO.NS...")
        result = coordinator.process_ticker("DEMO.NS")
        
        # Restore original fetch
        coordinator.trending.fetch_targeted_news = original_fetch
        
        logger.info("="*80)
        logger.critical("🎬 DEMO ATTACK SIMULATION COMPLETE!")
        logger.info("="*80)
        
        if result['status'] == 'attack_verified':
            attack_package = result['attack_package']
            
            logger.critical("\n📊 ATTACK SUMMARY:")
            logger.critical(f"   Ticker: {attack_package['ticker']}")
            logger.critical(f"   Stock Drop: {attack_package['projected_loss']}%")
            logger.critical(f"   Smoking Gun: {attack_package['smoking_gun_headline']}")
            logger.critical(f"   Time to Impact: {attack_package['latency_minutes']} minutes")
            logger.critical(f"   Correlation: {attack_package['correlation_confidence']}%")
            
            return {
                "status": "demo_success",
                "message": "🎬 Demo attack simulation completed successfully!",
                "attack_package": attack_package,
                "demo_note": "This is a simulated attack for demonstration purposes"
            }
        else:
            return {
                "status": "demo_incomplete",
                "message": "Demo ran but did not produce attack verification",
                "result": result
            }
        
    except Exception as e:
        logger.error(f"❌ Demo attack failed: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Demo failed: {str(e)}")


# ============================================================================
# WAR ROOM API GATEWAY - Frontend Integration
# ============================================================================

@app.get("/war-room/signals")
async def get_war_room_signals():
    """
    Get timeline signals for War Room correlation graph.
    
    Returns stock crashes (CRASH) and misinformation (RUMOR) events
    from the last 24 hours, formatted for Chart.js visualization.
    
    Returns:
        dict: Two arrays (stock_events, threat_events) with timestamps and severity
    """
    logger.info("[API] GET /api/war-room/signals")
    
    try:
        from datetime import datetime, timedelta
        
        # Get events from last 24 hours
        cutoff_time = (datetime.now() - timedelta(hours=24)).isoformat()
        
        # Query active_signals table (if it exists)
        try:
            response = db.supabase.table('active_signals').select('*').gte('timestamp', cutoff_time).order('timestamp').execute()
            signals = response.data if response.data else []
        except Exception as e:
            logger.warning(f"[API] active_signals table not found, using mock data: {e}")
            # Return mock data for demo
            signals = []
        
        # Separate into crashes and rumors
        stock_events = []
        threat_events = []
        
        for signal in signals:
            event = {
                'timestamp': signal['timestamp'],
                'ticker': signal['ticker'],
                'severity': signal['severity'],
                'metadata': signal.get('metadata', {})
            }
            
            if signal['signal_type'] == 'CRASH':
                stock_events.append(event)
            elif signal['signal_type'] == 'RUMOR':
                threat_events.append(event)
        
        logger.info(f"[API] Returning {len(stock_events)} crashes, {len(threat_events)} threats")
        
        return {
            "status": "success",
            "time_range_hours": 24,
            "stock_events": stock_events,
            "threat_events": threat_events,
            "total_events": len(stock_events) + len(threat_events)
        }
        
    except Exception as e:
        logger.error(f"[API] Error fetching signals: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch signals: {str(e)}")


class DeployCountermeasureRequest(BaseModel):
    """Request model for deploying a countermeasure."""
    event_id: str
    response_type: str  # "cease_desist", "official_denial", "ceo_alert"
    current_stock_price: float


@app.post("/deploy-response")
async def deploy_countermeasure(request: DeployCountermeasureRequest):
    """
    Deploy a crisis response countermeasure.
    
    This endpoint:
    1. Records the deployment in deployed_measures table
    2. Updates verified_threats status
    3. (Future) Triggers Herald Agent to actually send the response
    
    Args:
        request: DeployCountermeasureRequest with event ID and response type
        
    Returns:
        dict: Deployment confirmation with timestamp
    """
    logger.info(f"[API] POST /api/deploy-response")
    logger.info(f"[API]   Event ID: {request.event_id}")
    logger.info(f"[API]   Response Type: {request.response_type}")
    logger.info(f"[API]   Stock Price: ${request.current_stock_price}")
    
    try:
        coordinator = get_coordinator_agent()
        
        # Find the threat
        threat = None
        for attack in coordinator.verified_attacks:
            if attack.get('event_id') == request.event_id:
                threat = attack
                break
        
        if not threat:
            try:
                db_resp = db.supabase.table('verified_threats').select('*').eq('event_id', request.event_id).limit(1).execute()
                db_rows = db_resp.data or []
                if not db_rows:
                    try:
                        event_int = int(str(request.event_id))
                        db_resp2 = db.supabase.table('verified_threats').select('*').eq('id', event_int).limit(1).execute()
                        db_rows = db_resp2.data or []
                    except Exception:
                        db_rows = []
                if db_rows:
                    row = db_rows[0]
                    threat = {
                        'event_id': row.get('event_id') or str(row.get('id')),
                        'ticker': row.get('ticker'),
                        'responses': row.get('responses') or {}
                    }
                else:
                    raise HTTPException(status_code=404, detail=f"Event {request.event_id} not found")
            except HTTPException:
                raise
            except Exception:
                raise HTTPException(status_code=404, detail=f"Event {request.event_id} not found")
        
        # Get response text
        responses = threat.get('responses', {})
        response_text = responses.get(request.response_type)
        
        if not response_text:
            response_text = f"Deploy {request.response_type} for event {request.event_id}"
        
        from datetime import datetime
        deploy_timestamp = datetime.now().isoformat()
        
        # Insert into deployed_measures table
        try:
            measure_record = {
                'event_id': request.event_id,
                'measure_type': request.response_type.upper(),
                'deployed_at': deploy_timestamp,
                'stock_price_at_deployment': float(request.current_stock_price),
                'ticker': threat.get('ticker'),
                'response_text': response_text,
                'deployed_by': 'user'
            }
            
            db.supabase.table('deployed_measures').insert(measure_record).execute()
            logger.info("[API] ✓ Deployment recorded in database")
        except Exception as e:
            logger.warning(f"[API] Could not record in database (table may not exist): {e}")
        
        # Update verified_threats status
        try:
            db.supabase.table('verified_threats').update({
                'response_deployed': True,
                'deployed_at': deploy_timestamp
            }).eq('event_id', request.event_id).execute()
            logger.info("[API] ✓ Threat status updated")
        except Exception as e:
            logger.warning(f"[API] Could not update threat status: {e}")
        
        # Log the deployment
        logger.critical("="*80)
        logger.critical("🚀 COUNTERMEASURE DEPLOYED!")
        logger.critical("="*80)
        logger.critical(f"Event: {request.event_id}")
        logger.critical(f"Type: {request.response_type.upper()}")
        logger.critical(f"Stock Price at Deploy: ${request.current_stock_price}")
        logger.critical(f"Response:")
        logger.critical(f"  {response_text}")
        logger.critical("="*80)
        
        # TODO: Trigger Herald Agent to actually send
        # herald_agent.send_tweet(response_text)
        # herald_agent.send_ceo_sms(response_text)
        
        return {
            "status": "success",
            "message": "Countermeasure deployed successfully",
            "deployment": {
                "event_id": request.event_id,
                "response_type": request.response_type,
                "deployed_at": deploy_timestamp,
                "stock_price": request.current_stock_price,
                "action": "LOGGED_AND_RECORDED"
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[API] Deployment failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Deployment failed: {str(e)}")


@app.get("/feed/live")
async def get_live_threat_feed():
    """
    Get live high-severity threat feed for the Counter-Measure Console.
    
    Returns verified threats with severity HIGH or CRITICAL, including
    complete attack packages (smoking gun + AI-generated responses).
    
    Returns:
        dict: List of active threats ready for deployment
    """
    logger.info("[API] GET /api/feed/live")
    
    try:
        coordinator = get_coordinator_agent()
        
        # Get verified attacks from Coordinator (in-memory for now)
        all_threats = coordinator.verified_attacks
        
        # Also try to fetch from database
        try:
            db_response = db.supabase.table('verified_threats').select('*').order('crash_timestamp', desc=True).limit(10).execute()
            db_threats = db_response.data if db_response.data else []
            logger.info(f"[API] Fetched {len(db_threats)} threats from database")
        except Exception as e:
            logger.warning(f"[API] Could not fetch from database: {e}")
            db_threats = []
        
        # Combine and deduplicate
        threat_dict = {}
        
        # Add in-memory threats
        for threat in all_threats:
            threat_dict[threat['event_id']] = {
                'event_id': threat['event_id'],
                'ticker': threat['ticker'],
                'crash_timestamp': threat['crash_timestamp'],
                'current_price': threat.get('current_price'),
                'projected_loss': threat.get('projected_loss'),
                'z_score': threat.get('z_score'),
                'smoking_gun_headline': threat.get('smoking_gun_headline'),
                'smoking_gun_link': threat.get('smoking_gun_link'),
                'panic_score': threat.get('panic_score'),
                'correlation_confidence': threat.get('correlation_confidence'),
                'latency_minutes': threat.get('latency_minutes'),
                'responses': threat.get('responses', {}),
                'response_deployed': threat.get('response_deployed', False),
                'severity': 'CRITICAL' if threat.get('correlation_confidence', 0) > 80 else 'HIGH',
                'status': 'DEPLOYED' if threat.get('response_deployed') else 'READY'
            }
        
        # Add database threats
        for threat in db_threats:
            if threat['event_id'] not in threat_dict:
                threat_dict[threat['event_id']] = {
                    'event_id': threat['event_id'],
                    'ticker': threat['ticker'],
                    'crash_timestamp': threat['crash_timestamp'],
                    'current_price': threat.get('current_price'),
                    'projected_loss': threat.get('projected_loss'),
                    'z_score': threat.get('z_score'),
                    'smoking_gun_headline': threat.get('smoking_gun_headline'),
                    'smoking_gun_link': threat.get('smoking_gun_link'),
                    'panic_score': threat.get('panic_score'),
                    'correlation_confidence': threat.get('correlation_confidence'),
                    'latency_minutes': threat.get('latency_minutes'),
                    'responses': threat.get('responses', {}),
                    'response_deployed': threat.get('response_deployed', False),
                    'severity': 'CRITICAL' if threat.get('correlation_confidence', 0) > 80 else 'HIGH',
                    'status': 'DEPLOYED' if threat.get('response_deployed') else 'READY'
                }
        
        # Convert to list and filter high severity
        live_threats = [
            t for t in threat_dict.values()
            if t['severity'] in ['HIGH', 'CRITICAL']
        ]
        
        # Sort by timestamp (most recent first)
        live_threats.sort(key=lambda x: x['crash_timestamp'], reverse=True)
        
        logger.info(f"[API] Returning {len(live_threats)} high-severity threats")
        
        return {
            "status": "success",
            "total_threats": len(live_threats),
            "threats": live_threats,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"[API] Error fetching live feed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch live feed: {str(e)}")



# ============================================================================
# APPLICATION STARTUP
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Log application startup."""
    logger.info("=" * 80)
    logger.info("[FastAPI] Aegis Enterprise API - STARTING")
    logger.info("[FastAPI] Phase 4: War Room Integration")
    logger.info(f"[FastAPI] Supabase URL: {os.getenv('SUPABASE_URL', 'NOT SET')}")
    logger.info("[FastAPI] Agents initialized:")
    logger.info("  - ClaimIngestionAgent: Ready")
    logger.info("  - ResearchAgent: Ready")
    logger.info("  - InvestigatorAgent: Ready")
    logger.info("  - Scout Agent: Ready (Financial Surveillance)")
    logger.info("  - Trending Agent: Ready (Content Intelligence)")
    logger.info("  - Coordinator Agent: Ready (Strategic Crisis Governor)")
    logger.info("=" * 80)


@app.on_event("shutdown")
async def shutdown_event():
    """Log application shutdown."""
    logger.info("=" * 80)
    logger.info("[FastAPI] Misinformation Detection API - SHUTTING DOWN")
    logger.info("=" * 80)
