"""
Claim Ingestion Agent

This agent is responsible for processing and ingesting misinformation claims.
Phase 2: Returns dictionary responses only (no database integration yet).
"""

import hashlib
from typing import Dict, Optional


class ClaimIngestionAgent:
    """
    Agent responsible for ingesting claims into the system.
    Normalizes claim text and generates unique identifiers.
    """
    
    def __init__(self):
        """Initialize the Claim Ingestion Agent."""
        print("[ClaimIngestionAgent] Initialized")
    
    def ingest(self, claim_text: str, source_url: Optional[str] = None) -> Dict:
        """
        Ingest a claim for fact-checking.
        
        This method:
        1. Normalizes the claim text (lowercase, trim spaces)
        2. Computes a unique claim hash using SHA256
        3. Returns a JSON structure with claim details
        
        Args:
            claim_text (str): The text of the claim to be fact-checked
            source_url (Optional[str]): The URL source of the claim
        
        Returns:
            Dict: JSON structure containing claim_id, status, is_new, and normalized_text
        """
        print(f"[ClaimIngestionAgent] Ingesting claim: {claim_text[:50]}...")
        
        # Step 1: Normalize the claim text
        normalized_text = self._normalize_text(claim_text)
        print(f"[ClaimIngestionAgent] Normalized text: {normalized_text[:50]}...")
        
        # Step 2: Compute claim hash
        claim_hash = self._compute_claim_hash(normalized_text)
        print(f"[ClaimIngestionAgent] Computed claim hash: {claim_hash}")
        
        # Step 3: Build response JSON
        response = {
            "claim_id": claim_hash,
            "status": "pending",
            "is_new": True,
            "normalized_text": normalized_text
        }
        
        if source_url:
            print(f"[ClaimIngestionAgent] Source URL: {source_url}")
            response["source_url"] = source_url
        
        print(f"[ClaimIngestionAgent] Claim ingested successfully with ID: {claim_hash}")
        
        return response
    
    def _normalize_text(self, text: str) -> str:
        """
        Normalize claim text by converting to lowercase and trimming spaces.
        
        Args:
            text (str): Original claim text
        
        Returns:
            str: Normalized claim text
        """
        # Convert to lowercase
        normalized = text.lower()
        
        # Trim leading and trailing spaces
        normalized = normalized.strip()
        
        return normalized
    
    def _compute_claim_hash(self, normalized_text: str) -> str:
        """
        Compute SHA256 hash of the normalized claim text.
        
        Args:
            normalized_text (str): Normalized claim text
        
        Returns:
            str: Hexadecimal SHA256 hash
        """
        # Encode text to bytes
        text_bytes = normalized_text.encode('utf-8')
        
        # Compute SHA256 hash
        hash_object = hashlib.sha256(text_bytes)
        claim_hash = hash_object.hexdigest()
        
        return claim_hash
