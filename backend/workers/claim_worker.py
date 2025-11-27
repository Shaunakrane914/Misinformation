"""
Claim Worker

Asynchronous claim processing logic for the misinformation detection system.
This worker handles background processing of claims through the research and investigation pipeline.
"""

import logging
import traceback

from backend.agents.research_agent import ResearchAgent
from backend.agents.investigator_agent import InvestigatorAgent
from backend.db.database import (
    get_claim_by_id,
    update_claim_status,
    update_claim_final_result,
    insert_evidence
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


async def process_claim(claim_id: str):
    """
    Process a claim asynchronously through the research and investigation pipeline.
    
    This function:
    1. Fetches claim from database
    2. Sets claim status to "in_progress"
    3. Gathers evidence using ResearchAgent
    4. Determines verdict using InvestigatorAgent
    5. Inserts ONE evidence item (first refuting, else first supporting)
    6. Updates the database with final results
    7. Sets status to "completed" or "failed"
    
    Args:
        claim_id (str): Unique identifier for the claim
    """
    logger.info(f"[ClaimWorker] [{claim_id}] Starting claim processing")
    
    try:
        # Step 1: Fetch claim from database
        logger.info(f"[ClaimWorker] [{claim_id}] Fetching claim from database")
        claim = get_claim_by_id(claim_id)
        
        if not claim:
            logger.error(f"[ClaimWorker] [{claim_id}] Claim not found in database")
            return
        
        claim_text = claim.get("normalized_text") or claim.get("claim_text")
        logger.info(f"[ClaimWorker] [{claim_id}] Claim text: {claim_text[:100]}...")
        
        # Step 2: Update status to "in_progress"
        logger.info(f"[ClaimWorker] [{claim_id}] Updating status to 'in_progress'")
        update_claim_status(claim_id, "in_progress")
        
        # Step 3: Instantiate ResearchAgent
        logger.info(f"[ClaimWorker] [{claim_id}] Initializing ResearchAgent")
        research_agent = ResearchAgent()
        
        # Step 4: Gather evidence
        logger.info(f"[ClaimWorker] [{claim_id}] Running ResearchAgent.process()")
        evidence_json = research_agent.process(claim_text)
        
        logger.info(f"[ClaimWorker] [{claim_id}] Evidence gathering complete")
        logger.info(f"[ClaimWorker] [{claim_id}] Supporting evidence: {len(evidence_json.get('supporting_evidence', []))} points")
        logger.info(f"[ClaimWorker] [{claim_id}] Refuting evidence: {len(evidence_json.get('refuting_evidence', []))} points")
        
        # Step 5: Instantiate InvestigatorAgent
        logger.info(f"[ClaimWorker] [{claim_id}] Initializing InvestigatorAgent")
        investigator_agent = InvestigatorAgent()
        
        # Step 6: Determine verdict
        logger.info(f"[ClaimWorker] [{claim_id}] Running InvestigatorAgent.process()")
        verdict_json = investigator_agent.process(claim_text, evidence_json)
        
        logger.info(f"[ClaimWorker] [{claim_id}] Investigation complete")
        logger.info(f"[ClaimWorker] [{claim_id}] Verdict: {verdict_json.get('verdict')}")
        logger.info(f"[ClaimWorker] [{claim_id}] Confidence: {verdict_json.get('confidence')}")
        logger.info(f"[ClaimWorker] [{claim_id}] Severity: {verdict_json.get('severity')}")
        
        # Step 7: Reduce evidence to ONLY ONE
        # Pick first refuting evidence if available, else first supporting
        refuting_evidence = evidence_json.get('refuting_evidence', [])
        supporting_evidence = evidence_json.get('supporting_evidence', [])
        
        selected_evidence = None
        selected_stance = None
        
        if refuting_evidence and len(refuting_evidence) > 0:
            selected_evidence = refuting_evidence[0]
            selected_stance = "refuting"
            logger.info(f"[ClaimWorker] [{claim_id}] Selected refuting evidence")
        elif supporting_evidence and len(supporting_evidence) > 0:
            selected_evidence = supporting_evidence[0]
            selected_stance = "supporting"
            logger.info(f"[ClaimWorker] [{claim_id}] Selected supporting evidence")
        else:
            selected_evidence = "No evidence available"
            selected_stance = "neutral"
            logger.info(f"[ClaimWorker] [{claim_id}] No evidence available, using placeholder")
        
        # Step 8: Insert ONE evidence item into database
        logger.info(f"[ClaimWorker] [{claim_id}] Inserting evidence into database")
        insert_evidence(
            claim_id=claim_id,
            source_url=None,  # No URLs in current phase
            summary=selected_evidence,
            stance=selected_stance
        )
        
        # Step 9: Update claim with final results
        logger.info(f"[ClaimWorker] [{claim_id}] Updating claim with final results")
        update_claim_final_result(
            claim_id=claim_id,
            verdict=verdict_json.get("verdict"),
            confidence=verdict_json.get("confidence"),
            severity=verdict_json.get("severity"),
            reasoning=verdict_json.get("reasoning")
        )
        
        logger.info(f"[ClaimWorker] [{claim_id}] Processing completed successfully")
        logger.info(f"[ClaimWorker] [{claim_id}] Final verdict: {verdict_json.get('verdict')} "
                   f"(confidence: {verdict_json.get('confidence')}, severity: {verdict_json.get('severity')})")
        
    except Exception as e:
        # Handle any errors
        logger.error(f"[ClaimWorker] [{claim_id}] PROCESSING FAILED")
        logger.error(f"[ClaimWorker] [{claim_id}] Exception: {str(e)}")
        logger.error(f"[ClaimWorker] [{claim_id}] Full stack trace:")
        logger.error(traceback.format_exc())
        
        # Update database with failure status
        try:
            logger.info(f"[ClaimWorker] [{claim_id}] Updating status to 'failed'")
            update_claim_status(claim_id, "failed")
            
            # Update reasoning with error message
            from backend.db.database import supabase
            supabase.table("claims").update({
                "reasoning": f"Internal processing error: {str(e)}"
            }).eq("id", claim_id).execute()
            
            logger.info(f"[ClaimWorker] [{claim_id}] Error status updated in database")
        except Exception as db_error:
            logger.error(f"[ClaimWorker] [{claim_id}] Failed to update error status: {str(db_error)}")
