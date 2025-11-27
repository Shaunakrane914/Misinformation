"""
Database Module

Supabase database operations for the misinformation detection system.
Handles all CRUD operations for claims and evidence tables.
"""

import os
import logging
from typing import Dict, Optional, List
from supabase import create_client, Client
import uuid
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Initialize Supabase client
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    logger.warning("[Database] Supabase credentials not found in environment variables")
    logger.warning("[Database] Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY")
    supabase: Optional[Client] = None
else:
    try:
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        logger.info("[Database] Supabase client initialized successfully")
        logger.info(f"[Database] Connected to: {SUPABASE_URL}")
    except Exception as e:
        logger.error(f"[Database] Failed to initialize Supabase client: {str(e)}")
        supabase = None

_mem_claims: Dict[str, Dict] = {}
_mem_hash_index: Dict[str, str] = {}
_mem_evidence: Dict[str, List[Dict]] = {}


def insert_claim(claim_hash: str, claim_text: str, normalized_text: str) -> Dict:
    """
    Insert a new claim into the database.
    
    Args:
        claim_hash (str): SHA256 hash of the normalized claim text
        claim_text (str): Original claim text
        normalized_text (str): Normalized (lowercase, trimmed) claim text
    
    Returns:
        Dict: The inserted claim row
    
    Raises:
        Exception: If database operation fails
    """
    logger.info(f"[Database] Inserting claim with hash: {claim_hash}")
    logger.info(f"[Database] Claim text: {claim_text[:100]}...")
    
    if not supabase:
        claim_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        row = {
            "id": claim_id,
            "claim_hash": claim_hash,
            "claim_text": claim_text,
            "normalized_text": normalized_text,
            "status": "pending",
            "verdict": None,
            "confidence": None,
            "severity": None,
            "reasoning": None,
            "created_at": now,
            "updated_at": now
        }
        _mem_claims[claim_id] = row
        _mem_hash_index[claim_hash] = claim_id
        logger.info(f"[Database] [Memory] Claim inserted successfully with ID: {claim_id}")
        return row
    try:
        data = {
            "claim_hash": claim_hash,
            "claim_text": claim_text,
            "normalized_text": normalized_text,
            "status": "pending",
            "verdict": None,
            "confidence": None,
            "severity": None,
            "reasoning": None
        }
        response = supabase.table("claims").insert(data).execute()
        if not response.data:
            error_msg = "Failed to insert claim - no data returned"
            logger.error(f"[Database] {error_msg}")
            raise Exception(error_msg)
        claim_row = response.data[0]
        logger.info(f"[Database] Claim inserted successfully with ID: {claim_row.get('id')}")
        return claim_row
    except Exception as e:
        error_msg = f"Error inserting claim: {str(e)}"
        logger.error(f"[Database] {error_msg}")
        raise Exception(error_msg)


def get_claim_by_hash(claim_hash: str) -> Optional[Dict]:
    """
    Retrieve a claim by its hash.
    
    Args:
        claim_hash (str): SHA256 hash of the claim
    
    Returns:
        Optional[Dict]: Claim data or None if not found
    
    Raises:
        Exception: If database operation fails
    """
    logger.info(f"[Database] Retrieving claim by hash: {claim_hash}")
    
    if not supabase:
        claim_id = _mem_hash_index.get(claim_hash)
        if claim_id and claim_id in _mem_claims:
            logger.info(f"[Database] [Memory] Claim found with hash: {claim_hash}")
            return _mem_claims[claim_id]
        logger.info(f"[Database] [Memory] No claim found with hash: {claim_hash}")
        return None
    try:
        response = supabase.table("claims").select("*").eq("claim_hash", claim_hash).execute()
        if response.data and len(response.data) > 0:
            logger.info(f"[Database] Claim found with hash: {claim_hash}")
            return response.data[0]
        else:
            logger.info(f"[Database] No claim found with hash: {claim_hash}")
            return None
    except Exception as e:
        error_msg = f"Error retrieving claim by hash: {str(e)}"
        logger.error(f"[Database] {error_msg}")
        raise Exception(error_msg)


def get_claim_by_id(claim_id: str) -> Optional[Dict]:
    """
    Retrieve a claim by its ID.
    
    Args:
        claim_id (str): Claim ID (UUID or integer)
    
    Returns:
        Optional[Dict]: Claim data or None if not found
    
    Raises:
        Exception: If database operation fails
    """
    logger.info(f"[Database] Retrieving claim by ID: {claim_id}")
    
    if not supabase:
        row = _mem_claims.get(claim_id)
        if row:
            logger.info(f"[Database] [Memory] Claim found with ID: {claim_id}")
            return row
        logger.info(f"[Database] [Memory] No claim found with ID: {claim_id}")
        return None
    try:
        response = supabase.table("claims").select("*").eq("id", claim_id).execute()
        if response.data and len(response.data) > 0:
            logger.info(f"[Database] Claim found with ID: {claim_id}")
            return response.data[0]
        else:
            logger.info(f"[Database] No claim found with ID: {claim_id}")
            return None
    except Exception as e:
        error_msg = f"Error retrieving claim by ID: {str(e)}"
        logger.error(f"[Database] {error_msg}")
        raise Exception(error_msg)


def update_claim_status(claim_id: str, status: str) -> Dict:
    """
    Update the status of a claim.
    
    Args:
        claim_id (str): Claim ID
        status (str): New status (pending, in_progress, completed, failed)
    
    Returns:
        Dict: Updated claim row
    
    Raises:
        Exception: If database operation fails
    """
    logger.info(f"[Database] Updating claim {claim_id} status to: {status}")
    
    if not supabase:
        row = _mem_claims.get(claim_id)
        if not row:
            error_msg = f"Claim {claim_id} not found"
            logger.error(f"[Database] [Memory] {error_msg}")
            raise Exception(error_msg)
        row["status"] = status
        row["updated_at"] = datetime.utcnow().isoformat()
        logger.info(f"[Database] [Memory] Claim {claim_id} status updated successfully")
        return row
    try:
        response = supabase.table("claims").update({
            "status": status
        }).eq("id", claim_id).execute()
        if not response.data:
            error_msg = f"Failed to update claim {claim_id} - no data returned"
            logger.error(f"[Database] {error_msg}")
            raise Exception(error_msg)
        logger.info(f"[Database] Claim {claim_id} status updated successfully")
        return response.data[0]
    except Exception as e:
        error_msg = f"Error updating claim status: {str(e)}"
        logger.error(f"[Database] {error_msg}")
        raise Exception(error_msg)


def update_claim_final_result(
    claim_id: str,
    verdict: str,
    confidence: float,
    severity: str,
    reasoning: str
) -> Dict:
    """
    Update a claim with final investigation results.
    
    Args:
        claim_id (str): Claim ID
        verdict (str): Final verdict (True, False, Misleading, Unverified)
        confidence (float): Confidence score (0.0 to 1.0)
        severity (str): Severity level (Low, Medium, High)
        reasoning (str): Explanation for the verdict
    
    Returns:
        Dict: Updated claim row
    
    Raises:
        Exception: If database operation fails
    """
    logger.info(f"[Database] Updating claim {claim_id} with final results")
    logger.info(f"[Database] Verdict: {verdict}, Confidence: {confidence}, Severity: {severity}")
    
    if not supabase:
        row = _mem_claims.get(claim_id)
        if not row:
            error_msg = f"Claim {claim_id} not found"
            logger.error(f"[Database] [Memory] {error_msg}")
            raise Exception(error_msg)
        row["verdict"] = verdict
        row["confidence"] = confidence
        row["severity"] = severity
        row["reasoning"] = reasoning
        row["status"] = "completed"
        row["updated_at"] = datetime.utcnow().isoformat()
        logger.info(f"[Database] [Memory] Claim {claim_id} updated with final results successfully")
        return row
    try:
        response = supabase.table("claims").update({
            "verdict": verdict,
            "confidence": confidence,
            "severity": severity,
            "reasoning": reasoning,
            "status": "completed"
        }).eq("id", claim_id).execute()
        if not response.data:
            error_msg = f"Failed to update claim {claim_id} with final results - no data returned"
            logger.error(f"[Database] {error_msg}")
            raise Exception(error_msg)
        logger.info(f"[Database] Claim {claim_id} updated with final results successfully")
        return response.data[0]
    except Exception as e:
        error_msg = f"Error updating claim final results: {str(e)}"
        logger.error(f"[Database] {error_msg}")
        raise Exception(error_msg)


def insert_evidence(
    claim_id: str,
    source_url: Optional[str],
    summary: str,
    stance: str
) -> Dict:
    """
    Insert evidence for a claim.
    
    Args:
        claim_id (str): Claim ID this evidence is associated with
        source_url (Optional[str]): URL of the evidence source
        summary (str): Summary of the evidence
        stance (str): Evidence stance (supporting, refuting, neutral)
    
    Returns:
        Dict: The inserted evidence row
    
    Raises:
        Exception: If database operation fails
    """
    logger.info(f"[Database] Inserting evidence for claim: {claim_id}")
    logger.info(f"[Database] Stance: {stance}, Source: {source_url or 'None'}")
    
    if not supabase:
        ev = {
            "id": str(uuid.uuid4()),
            "claim_id": claim_id,
            "source_url": source_url,
            "summary": summary,
            "stance": stance,
            "created_at": datetime.utcnow().isoformat()
        }
        _mem_evidence.setdefault(claim_id, []).append(ev)
        logger.info(f"[Database] [Memory] Evidence inserted successfully for claim {claim_id}")
        return ev
    try:
        stance_value = stance
        if stance_value == "supporting":
            stance_value = "support"
        elif stance_value == "refuting":
            stance_value = "refute"
        elif stance_value not in ("support", "refute", "neutral"):
            stance_value = "neutral"
        data = {
            "claim_id": claim_id,
            "source_url": source_url or "",
            "summary": summary,
            "stance": stance_value
        }
        response = supabase.table("evidence").insert(data).execute()
        if not response.data:
            error_msg = "Failed to insert evidence - no data returned"
            logger.error(f"[Database] {error_msg}")
            raise Exception(error_msg)
        evidence_row = response.data[0]
        logger.info(f"[Database] Evidence inserted successfully with ID: {evidence_row.get('id')}")
        return evidence_row
    except Exception as e:
        error_msg = f"Error inserting evidence: {str(e)}"
        logger.error(f"[Database] {error_msg}")
        raise Exception(error_msg)


def get_evidence_by_claim_id(claim_id: str) -> List[Dict]:
    """
    Retrieve all evidence for a specific claim.
    
    Args:
        claim_id (str): Claim ID
    
    Returns:
        List[Dict]: List of evidence rows
    
    Raises:
        Exception: If database operation fails
    """
    logger.info(f"[Database] Retrieving evidence for claim: {claim_id}")
    
    if not supabase:
        items = _mem_evidence.get(claim_id, [])
        logger.info(f"[Database] [Memory] Found {len(items)} evidence items for claim {claim_id}")
        return items
    try:
        response = supabase.table("evidence").select("*").eq("claim_id", claim_id).execute()
        logger.info(f"[Database] Found {len(response.data)} evidence items for claim {claim_id}")
        return response.data
    except Exception as e:
        error_msg = f"Error retrieving evidence: {str(e)}"
        logger.error(f"[Database] {error_msg}")
        raise Exception(error_msg)
