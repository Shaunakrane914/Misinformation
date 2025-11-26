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

@app.get("/")
async def root():
    """Root endpoint with API information."""
    logger.info("[API] Root endpoint accessed")
    return {
        "message": "Misinformation Detection API",
        "version": "2.0.0",
        "storage": "Supabase Database",
        "endpoints": {
            "submit_claim": "POST /claims/submit",
            "check_status": "GET /claims/{claim_id}"
        }
    }


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
async def get_dashboard_claims():
    logger.info("[API] GET /dashboard/claims - Generating dashboard claims")
    try:
        claims = load_random_dashboard_claims(n=15)
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
        return results
    except Exception as e:
        logger.error(f"[API] Error generating dashboard claims: {str(e)}")
        raise HTTPException(status_code=500, detail="Error generating dashboard claims")


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
