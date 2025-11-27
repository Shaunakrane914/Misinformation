"""
Claim Schemas

Pydantic models for API request/response validation in the misinformation detection system.
"""

from pydantic import BaseModel


class SubmitClaimRequest(BaseModel):
    """
    Request model for submitting a claim to the fact-checking system.
    
    Attributes:
        claim_text (str): The text of the claim to be fact-checked
    """
    claim_text: str


class SubmitClaimResponse(BaseModel):
    """
    Response model after submitting a claim.
    
    Attributes:
        claim_id (str): Unique identifier for the submitted claim (SHA256 hash)
        status (str): Current processing status ("pending", "in_progress", "completed", "failed")
    """
    claim_id: str
    status: str


class ClaimResult(BaseModel):
    """
    Complete result model for a claim, including all processing details.
    
    This model represents the full state of a claim including:
    - The original claim text
    - Processing status
    - Verdict from the investigator agent
    - Confidence score and severity level
    - Reasoning for the verdict
    - Evidence summary
    
    Attributes:
        claim_id (str): Unique identifier for the claim
        claim_text (str): The normalized claim text
        status (str): Processing status ("pending", "in_progress", "completed", "failed")
        verdict (str | None): Final verdict ("True", "False", "Misleading", "Unverified")
        confidence (float | None): Confidence score from 0.0 to 1.0
        severity (str | None): Severity level ("Low", "Medium", "High")
        reasoning (str | None): Brief explanation of the verdict
        evidence (dict | None): Single evidence entry with structure:
                                {"source_url": str, "summary": str, "type": str}
    """
    claim_id: str
    claim_text: str
    status: str
    verdict: str | None = None
    confidence: float | None = None
    severity: str | None = None
    reasoning: str | None = None
    evidence: dict | None = None
