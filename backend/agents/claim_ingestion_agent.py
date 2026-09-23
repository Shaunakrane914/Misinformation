"""
Aegis Protocol — Claim Ingestion Agent
======================================
Ingests, normalizes (Unicode NFC, whitespace collapsing, punctuation trimming),
validates, and deduplicates incoming claims against the persistent database.
"""

import hashlib
import logging
import re
import unicodedata
from typing import Dict, Optional, List, Any

from backend.db.database import get_claim_by_hash, insert_claim

logger = logging.getLogger(__name__)


class ClaimIngestionAgent:
    """
    Agent responsible for deterministic ingestion, Unicode normalization,
    and database-backed deduplication of misinformation claims.
    """

    def __init__(self):
        logger.info("[ClaimIngestionAgent] Initialized with Unicode normalization and DB deduplication")

    def normalize_text(self, text: str) -> str:
        """
        Normalize claim text:
        1. Unicode NFC normalization
        2. Replace smart quotes / dashes with ASCII equivalents
        3. Collapse multi-spaces, newlines, and tabs into single spaces
        4. Lowercase and strip leading/trailing whitespace and outer quotation marks
        """
        if not text:
            return ""

        # Step 1: Unicode NFC normalization
        norm = unicodedata.normalize("NFC", text)

        # Step 2: Normalize typographical quotes and dashes
        norm = norm.replace("“", '"').replace("”", '"')
        norm = norm.replace("‘", "'").replace("’", "'")
        norm = norm.replace("—", "-").replace("–", "-")

        # Step 3: Collapse whitespace
        norm = re.sub(r"\s+", " ", norm).strip()

        # Step 4: Lowercase and strip outer quotes / trailing punctuation
        norm = norm.lower().strip()
        if (norm.startswith('"') and norm.endswith('"')) or (norm.startswith("'") and norm.endswith("'")):
            norm = norm[1:-1].strip()
        norm = norm.rstrip("!?. \t\r\n")

        return norm

    def compute_claim_hash(self, normalized_text: str) -> str:
        """Compute SHA256 hex digest for normalized claim text."""
        return hashlib.sha256(normalized_text.encode("utf-8")).hexdigest()

    # Aliases
    normalize = normalize_text
    compute_hash = compute_claim_hash

    def ingest(self, claim_text: str, source_url: Optional[str] = None) -> Dict:
        """
        Ingest a claim with validation, normalization, and deduplication.
        
        Args:
            claim_text: Raw claim text submitted
            source_url: Optional source URL where the claim originated
            
        Returns:
            Dict containing claim_id, status, is_new, normalized_text, and claim_hash
        """
        raw_text = (claim_text or "").strip()
        if len(raw_text) < 5:
            raise ValueError("Claim text is too short (minimum 5 characters required).")
        if len(raw_text) > 5000:
            raise ValueError("Claim text exceeds maximum permitted length (5000 characters).")

        normalized = self.normalize_text(raw_text)
        claim_hash = self.compute_claim_hash(normalized)

        # Check database for existing claim (Idempotency & Deduplication)
        existing_claim = get_claim_by_hash(claim_hash)
        if existing_claim:
            logger.info(f"[ClaimIngestionAgent] Duplicate claim detected (hash={claim_hash[:10]}..., id={existing_claim.get('id')})")
            return {
                "claim_id": str(existing_claim.get("id")),
                "claim_hash": claim_hash,
                "status": existing_claim.get("status", "completed"),
                "is_new": False,
                "original_text": existing_claim.get("claim_text", raw_text),
                "normalized_text": normalized,
                "verdict": existing_claim.get("verdict"),
                "confidence": existing_claim.get("confidence"),
                "source_url": existing_claim.get("source_url") or source_url
            }

        # Insert new claim
        claim_row = insert_claim(
            claim_hash=claim_hash,
            claim_text=raw_text,
            normalized_text=normalized,
            source_url=source_url
        )

        claim_id = str(claim_row.get("id"))
        logger.info(f"[ClaimIngestionAgent] New claim registered with ID: {claim_id}")

        return {
            "claim_id": claim_id,
            "claim_hash": claim_hash,
            "status": "pending",
            "is_new": True,
            "original_text": raw_text,
            "normalized_text": normalized,
            "source_url": source_url
        }

    def decompose_claim(self, claim_text: str) -> List["AtomicClaim"]:
        """
        Decompose a compound claim statement into verifiable atomic claims.
        Extracts entities, verifiable dimensions, and assigns unique claim IDs.
        """
        from backend.services.research.research_models import AtomicClaim

        raw = (claim_text or "").strip()
        if not raw:
            return []

        # Split on sentence boundaries or strong coordinating conjunctions
        parts = [p.strip() for p in re.split(r'(?<=[.?!])\s+|\s+(?:and also|additionally|furthermore|claiming that)\s+', raw) if len(p.strip()) > 8]
        if not parts:
            parts = [raw]

        atomic_claims: List[AtomicClaim] = []
        for idx, part in enumerate(parts):
            # Extract potential entities
            words = re.findall(r'\b[A-Z][a-zA-Z0-9_]+\b', part)
            entity = words[0] if words else "Unknown Entity"
            
            # Extract verifiable dimensions
            dims = []
            if re.search(r'[\$₹€£]|\b\d+(?:\.\d+)?%|\b\d+\b', part):
                dims.append("QUANTITATIVE_VALUE")
            if re.search(r'\b(?:19|20)\d{2}\b|\b(?:today|yesterday|january|february|march|april|may|june|july|august|september|october|november|december)\b', part, re.I):
                dims.append("TEMPORAL_ANCHOR")
            if any(w in part.lower() for w in ["acquired", "bought", "merger", "cured", "died", "arrested", "filed", "resigned", "announced"]):
                dims.append("ACTION_EVENT")
            if not dims:
                dims.append("GENERAL_ASSERTION")

            c_id = f"atomic_{idx + 1:02d}"
            atomic_claims.append(AtomicClaim(
                claim_id=c_id,
                claim_text=part,
                entity=entity,
                claim_type="FACTUAL",
                verifiable_dimensions=dims
            ))

        return atomic_claims


claim_ingestion_agent = ClaimIngestionAgent()


def get_claim_ingestion_agent() -> ClaimIngestionAgent:
    """Return singleton instance of ClaimIngestionAgent."""
    return claim_ingestion_agent

