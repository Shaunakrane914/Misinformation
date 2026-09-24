"""
Database Module

Supabase database operations for the misinformation detection system.
Handles all CRUD operations for claims and evidence tables with resilient in-memory fallback.
"""

import os
import logging
from typing import Dict, Optional, List, Any
import json
import uuid
from datetime import datetime
from supabase import create_client, Client

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

# Resilient in-memory fallback caches & local SQLite persistence
_mem_claims: Dict[str, Dict] = {}
_mem_hash_index: Dict[str, str] = {}
_mem_evidence: Dict[str, List[Dict]] = {}
_mem_research: Dict[str, Dict] = {}

import sqlite3

SQLITE_DB_PATH = os.getenv("AEGIS_SQLITE_PATH", os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "aegis_local.db")))

def _init_sqlite_db():
    """Initialize local SQLite database for offline and resilient persistence."""
    try:
        conn = sqlite3.connect(SQLITE_DB_PATH)
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS claims (
                id TEXT PRIMARY KEY,
                claim_hash TEXT UNIQUE,
                claim_text TEXT,
                normalized_text TEXT,
                source_url TEXT,
                status TEXT,
                verdict TEXT,
                confidence REAL,
                severity TEXT,
                reasoning TEXT,
                created_at TEXT,
                updated_at TEXT
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS evidence (
                id TEXT PRIMARY KEY,
                claim_id TEXT,
                evidence_text TEXT,
                summary TEXT,
                source_url TEXT,
                source_name TEXT,
                credibility_score REAL,
                stance TEXT,
                created_at TEXT
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS claim_research (
                claim_id TEXT PRIMARY KEY,
                funnel_json TEXT,
                corpus_json TEXT,
                created_at TEXT
            )
        """)
        conn.commit()

        # Warm up in-memory caches from SQLite
        cur.execute("SELECT id, claim_hash, claim_text, normalized_text, source_url, status, verdict, confidence, severity, reasoning, created_at, updated_at FROM claims")
        for row in cur.fetchall():
            c_dict = {
                "id": row[0],
                "claim_hash": row[1],
                "claim_text": row[2],
                "normalized_text": row[3],
                "source_url": row[4],
                "status": row[5],
                "verdict": row[6],
                "confidence": row[7],
                "severity": row[8],
                "reasoning": row[9],
                "created_at": row[10],
                "updated_at": row[11],
            }
            _mem_claims[row[0]] = c_dict
            if row[1]:
                _mem_hash_index[row[1]] = row[0]

        cur.execute("SELECT id, claim_id, evidence_text, summary, source_url, source_name, credibility_score, stance, created_at FROM evidence")
        for row in cur.fetchall():
            e_dict = {
                "id": row[0],
                "claim_id": row[1],
                "evidence_text": row[2],
                "summary": row[3],
                "source_url": row[4],
                "source_name": row[5],
                "credibility_score": row[6],
                "stance": row[7],
                "created_at": row[8],
            }
            cid = row[1]
            if cid not in _mem_evidence:
                _mem_evidence[cid] = []
            _mem_evidence[cid].append(e_dict)

        cur.execute("SELECT claim_id, funnel_json, corpus_json, created_at FROM claim_research")
        for row in cur.fetchall():
            try:
                _mem_research[row[0]] = {
                    "claim_id": row[0],
                    "funnel": json.loads(row[1]) if row[1] else {},
                    "corpus": json.loads(row[2]) if row[2] else {},
                    "created_at": row[3],
                }
            except Exception:
                pass

        conn.close()
        logger.info(f"[Database] SQLite persistence initialized at: {SQLITE_DB_PATH} (loaded {len(_mem_claims)} claims)")
    except Exception as e:
        logger.warning(f"[Database] SQLite init note: {e}")

# Run SQLite initialization
_init_sqlite_db()


def _sqlite_upsert_claim(row: Dict):
    try:
        conn = sqlite3.connect(SQLITE_DB_PATH)
        cur = conn.cursor()
        cur.execute("""
            INSERT OR REPLACE INTO claims (
                id, claim_hash, claim_text, normalized_text, source_url,
                status, verdict, confidence, severity, reasoning, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            row.get("id"), row.get("claim_hash"), row.get("claim_text"), row.get("normalized_text"), row.get("source_url"),
            row.get("status"), row.get("verdict"), row.get("confidence"), row.get("severity"), row.get("reasoning"),
            row.get("created_at"), row.get("updated_at")
        ))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.debug(f"[Database] SQLite claim upsert notice: {e}")


def _sqlite_insert_evidence(row: Dict):
    try:
        conn = sqlite3.connect(SQLITE_DB_PATH)
        cur = conn.cursor()
        cur.execute("""
            INSERT OR REPLACE INTO evidence (
                id, claim_id, evidence_text, summary, source_url, source_name,
                credibility_score, stance, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            row.get("id"), row.get("claim_id"), row.get("evidence_text"), row.get("summary"),
            row.get("source_url"), row.get("source_name"), row.get("credibility_score"),
            row.get("stance"), row.get("created_at")
        ))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.debug(f"[Database] SQLite evidence insert notice: {e}")


def _mem_insert_claim(claim_hash: str, claim_text: str, normalized_text: str, source_url: Optional[str] = None) -> Dict:
    claim_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    row = {
        "id": claim_id,
        "claim_hash": claim_hash,
        "claim_text": claim_text,
        "normalized_text": normalized_text,
        "source_url": source_url,
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
    _sqlite_upsert_claim(row)
    logger.info(f"[Database] [Memory+SQLite] Claim inserted with ID: {claim_id}")
    return row


def insert_claim(claim_hash: str, claim_text: str, normalized_text: str, source_url: Optional[str] = None) -> Dict:
    """Insert a new claim into Supabase with automatic in-memory fallback."""
    logger.info(f"[Database] Inserting claim with hash: {claim_hash}")
    
    if supabase:
        try:
            data = {
                "claim_hash": claim_hash,
                "claim_text": claim_text,
                "normalized_text": normalized_text,
                "source_url": source_url,
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
    
    return _mem_insert_claim(claim_hash, claim_text, normalized_text, source_url=source_url)


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
                _sqlite_upsert_claim(claim_row)
                return claim_row
        except Exception as e:
            logger.warning(f"[Database] Supabase status update failed ({e}), updating memory.")
    
    row = _mem_claims.get(str(claim_id), {})
    row["status"] = status
    row["updated_at"] = datetime.utcnow().isoformat()
    _mem_claims[str(claim_id)] = row
    _sqlite_upsert_claim(row)
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
                _sqlite_upsert_claim(claim_row)
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
    _sqlite_upsert_claim(row)
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
                _sqlite_insert_evidence(evidence_row)
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
    _sqlite_insert_evidence(row)
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


# ─────────────────────────────────────────────────────────────────────────────
# CLAIM RESEARCH CORPUS OPERATIONS
# ─────────────────────────────────────────────────────────────────────────────

def save_claim_research(claim_id: str, corpus: Dict[str, Any]) -> bool:
    """Save full research corpus and extract lightweight funnel metrics."""
    try:
        if not claim_id or not corpus:
            return False

        # Extract or construct structured funnel
        raw_funnel = corpus.get("funnel") or {}
        funnel = {
            "queries_planned": raw_funnel.get("queries_planned") or corpus.get("queries_planned") or 0,
            "queries_executed": raw_funnel.get("queries_executed") or corpus.get("queries_executed") or 0,
            "candidates_found": raw_funnel.get("candidates_found") or len(corpus.get("raw_candidates", [])) or corpus.get("candidates_found") or 0,
            "candidates_ranked": raw_funnel.get("candidates_ranked") or len(corpus.get("ranked_candidates", [])) or corpus.get("candidates_ranked") or 0,
            "deep_reads_count": raw_funnel.get("deep_reads_count") or len(corpus.get("deep_read_sources", [])) or corpus.get("deep_read_success") or 0,
            "primary_sources_count": raw_funnel.get("primary_sources_count") or len(corpus.get("primary_sources", [])) or corpus.get("primary_sources_found") or 0,
            "independent_groups_count": raw_funnel.get("independent_groups_count") or len(corpus.get("corroboration_groups", [])) or corpus.get("independent_source_groups") or 0,
            "contradictions_count": raw_funnel.get("contradictions_count") or len(corpus.get("contradictions", [])) or corpus.get("contradictions_found") or 0,
            "findings_count": raw_funnel.get("findings_count") or len(corpus.get("grounded_findings", [])) or corpus.get("findings_count") or 0,
        }

        created_at = datetime.utcnow().isoformat()
        _mem_research[str(claim_id)] = {
            "claim_id": str(claim_id),
            "funnel": funnel,
            "corpus": corpus,
            "created_at": created_at,
        }

        try:
            conn = sqlite3.connect(SQLITE_DB_PATH)
            cur = conn.cursor()
            cur.execute("""
                INSERT OR REPLACE INTO claim_research (claim_id, funnel_json, corpus_json, created_at)
                VALUES (?, ?, ?, ?)
            """, (str(claim_id), json.dumps(funnel), json.dumps(corpus), created_at))
            conn.commit()
            conn.close()
        except Exception as e_sql:
            logger.warning(f"[Database] SQLite save_claim_research notice: {e_sql}")

        return True
    except Exception as e:
        logger.error(f"[Database] save_claim_research error: {e}")
        return False


def get_claim_research(claim_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve full research corpus by claim_id."""
    if not claim_id:
        return None
    cid = str(claim_id)
    if cid in _mem_research:
        return _mem_research[cid].get("corpus")

    try:
        conn = sqlite3.connect(SQLITE_DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT corpus_json FROM claim_research WHERE claim_id = ?", (cid,))
        row = cur.fetchone()
        conn.close()
        if row and row[0]:
            corpus_data = json.loads(row[0])
            _mem_research.setdefault(cid, {})["corpus"] = corpus_data
            return corpus_data
    except Exception as e:
        logger.warning(f"[Database] SQLite get_claim_research error: {e}")
    return None


def get_claim_research_funnel(claim_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve lightweight funnel summary metrics by claim_id."""
    if not claim_id:
        return None
    cid = str(claim_id)
    if cid in _mem_research:
        return _mem_research[cid].get("funnel")

    try:
        conn = sqlite3.connect(SQLITE_DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT funnel_json FROM claim_research WHERE claim_id = ?", (cid,))
        row = cur.fetchone()
        conn.close()
        if row and row[0]:
            funnel_data = json.loads(row[0])
            _mem_research.setdefault(cid, {})["funnel"] = funnel_data
            return funnel_data
    except Exception as e:
        logger.warning(f"[Database] SQLite get_claim_research_funnel error: {e}")
    return None
