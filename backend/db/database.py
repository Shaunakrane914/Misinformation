"""
Database Module

Supabase database operations for the misinformation detection system.
Handles all CRUD operations for claims and evidence tables with resilient in-memory fallback.
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

supabase: Optional[Client] = None
if not SUPABASE_URL or not SUPABASE_KEY:
    logger.warning("[Database] Supabase credentials not found in environment variables. Using in-memory store.")
else:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        logger.info("[Database] Supabase client initialized successfully")
        logger.info(f"[Database] Connected to: {SUPABASE_URL}")
    except Exception as e:
        logger.error(f"[Database] Failed to initialize Supabase client: {str(e)}")
        supabase = None

# Resilient in-memory fallback caches
_mem_claims: Dict[str, Dict] = {}
_mem_hash_index: Dict[str, str] = {}
_mem_evidence: Dict[str, List[Dict]] = {}


def _mem_insert_claim(claim_hash: str, claim_text: str, normalized_text: str) -> Dict:
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
    logger.info(f"[Database] [Memory] Claim inserted with ID: {claim_id}")
    return row


def insert_claim(claim_hash: str, claim_text: str, normalized_text: str) -> Dict:
    """Insert a new claim into Supabase with automatic in-memory fallback."""
    logger.info(f"[Database] Inserting claim with hash: {claim_hash}")
    
    if supabase:
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
            if response.data:
                claim_row = response.data[0]
                logger.info(f"[Database] Claim inserted successfully with ID: {claim_row.get('id')}")
                _mem_claims[str(claim_row.get('id'))] = claim_row
                _mem_hash_index[claim_hash] = str(claim_row.get('id'))
                return claim_row
        except Exception as e:
            logger.warning(f"[Database] Supabase insert failed ({e}), using memory fallback.")
    
    return _mem_insert_claim(claim_hash, claim_text, normalized_text)


def get_claim_by_hash(claim_hash: str) -> Optional[Dict]:
    """Retrieve a claim by its hash."""
    logger.info(f"[Database] Retrieving claim by hash: {claim_hash}")
    
    if supabase:
        try:
            response = supabase.table("claims").select("*").eq("claim_hash", claim_hash).execute()
            if response.data and len(response.data) > 0:
                logger.info(f"[Database] Claim found with hash: {claim_hash}")
                return response.data[0]
            else:
                return None
        except Exception as e:
            logger.warning(f"[Database] Supabase fetch by hash failed ({e}), checking memory.")
    
    claim_id = _mem_hash_index.get(claim_hash)
    if claim_id and claim_id in _mem_claims:
        return _mem_claims[claim_id]
    return None


def get_claim_by_id(claim_id: str) -> Optional[Dict]:
    """Retrieve a claim by its ID."""
    logger.info(f"[Database] Retrieving claim by ID: {claim_id}")
    
    if supabase:
        try:
            response = supabase.table("claims").select("*").eq("id", claim_id).execute()
            if response.data and len(response.data) > 0:
                logger.info(f"[Database] Claim found with ID: {claim_id}")
                return response.data[0]
        except Exception as e:
            logger.warning(f"[Database] Supabase fetch by ID failed ({e}), checking memory.")
    
    return _mem_claims.get(str(claim_id))


def get_all_claims(limit: int = 50) -> List[Dict]:
    """Retrieve recent claims."""
    if supabase:
        try:
            resp = supabase.table("claims").select("*").order("created_at", desc=True).limit(limit).execute()
            if resp.data:
                return resp.data
        except Exception as e:
            logger.warning(f"[Database] get_all_claims Supabase fallback: {e}")
    return list(_mem_claims.values())[:limit]


def update_claim_status(claim_id: str, status: str) -> Dict:
    """Update claim processing status."""
    logger.info(f"[Database] Updating claim status: ID={claim_id}, status={status}")
    
    if supabase:
        try:
            now = datetime.utcnow().isoformat()
            data = {"status": status, "updated_at": now}
            response = supabase.table("claims").update(data).eq("id", claim_id).execute()
            if response.data:
                claim_row = response.data[0]
                _mem_claims[str(claim_id)] = claim_row
                return claim_row
        except Exception as e:
            logger.warning(f"[Database] Supabase status update failed ({e}), updating memory.")
    
    row = _mem_claims.get(str(claim_id), {})
    row["status"] = status
    row["updated_at"] = datetime.utcnow().isoformat()
    _mem_claims[str(claim_id)] = row
    return row


def update_claim_verdict(
    claim_id: str,
    verdict: str,
    confidence: float,
    severity: str,
    reasoning: str
) -> Dict:
    """Update claim with final verification verdict."""
    logger.info(f"[Database] Updating claim verdict: ID={claim_id}, verdict={verdict}, confidence={confidence}")
    
    if supabase:
        try:
            now = datetime.utcnow().isoformat()
            data = {
                "verdict": verdict,
                "confidence": confidence,
                "severity": severity,
                "reasoning": reasoning,
                "status": "completed",
                "updated_at": now
            }
            response = supabase.table("claims").update(data).eq("id", claim_id).execute()
            if response.data:
                claim_row = response.data[0]
                _mem_claims[str(claim_id)] = claim_row
                return claim_row
        except Exception as e:
            logger.warning(f"[Database] Supabase verdict update failed ({e}), updating memory.")
    
    row = _mem_claims.get(str(claim_id), {})
    row.update({
        "verdict": verdict,
        "confidence": confidence,
        "severity": severity,
        "reasoning": reasoning,
        "status": "completed",
        "updated_at": datetime.utcnow().isoformat()
    })
    _mem_claims[str(claim_id)] = row
    return row


def insert_evidence(
    claim_id: str,
    evidence_text: str = "",
    source_url: Optional[str] = None,
    source_name: Optional[str] = "Source",
    credibility_score: float = 0.8,
    stance: str = "neutral",
    summary: Optional[str] = None,
    **kwargs
) -> Dict:
    """Insert evidence linked to a claim."""
    text_content = evidence_text or summary or ""
    logger.info(f"[Database] Inserting evidence for claim ID: {claim_id}")
    
    if supabase:
        try:
            data = {
                "claim_id": claim_id,
                "evidence_text": text_content,
                "source_url": source_url,
                "source_name": source_name or "Source",
                "credibility_score": credibility_score,
                "stance": stance
            }
            response = supabase.table("evidence").insert(data).execute()
            if response.data:
                evidence_row = response.data[0]
                return evidence_row
        except Exception as e:
            logger.warning(f"[Database] Supabase insert evidence failed ({e}), writing memory.")
    
    evidence_id = str(uuid.uuid4())
    row = {
        "id": evidence_id,
        "claim_id": claim_id,
        "evidence_text": text_content,
        "summary": text_content,
        "source_url": source_url,
        "source_name": source_name,
        "credibility_score": credibility_score,
        "stance": stance,
        "created_at": datetime.utcnow().isoformat()
    }
    if claim_id not in _mem_evidence:
        _mem_evidence[claim_id] = []
    _mem_evidence[claim_id].append(row)
    return row


def get_evidence_by_claim_id(claim_id: str) -> List[Dict]:
    """Retrieve all evidence linked to a claim ID."""
    if supabase:
        try:
            response = supabase.table("evidence").select("*").eq("claim_id", claim_id).execute()
            if response.data:
                return response.data
        except Exception as e:
            logger.warning(f"[Database] Supabase get evidence failed ({e}), checking memory.")
    
    return _mem_evidence.get(str(claim_id), [])


# Aliases for compatibility
update_claim_final_result = update_claim_verdict
