"""
FastAPI Backend for Misinformation Detection System

Phase 3: Database integration with Supabase.
All claims and evidence stored in database.
"""

import os
from typing import Dict, Optional, List
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel
import logging
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

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
        return dashboard_claims
        
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
        
        # Use Gemini to generate explanation
        import google.generativeai as genai
        response = research_agent.client.models.generate_content(
            model=research_agent.model_name,
            contents=prompt_text
        )
        
        explanation = response.text.strip()
        
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
