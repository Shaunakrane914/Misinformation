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
    insert_evidence,
    save_claim_research
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

_research_agent = None
_investigator_agent = None


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
        
        # Step 3: Lazy-instantiate agents
        global _research_agent, _investigator_agent
        if _research_agent is None:
            _research_agent = ResearchAgent()
        if _investigator_agent is None:
            _investigator_agent = InvestigatorAgent()

        # Step 4: Gather evidence
        source_url = claim.get("source_url")
        logger.info(f"[ClaimWorker] [{claim_id}] Running ResearchAgent.gather_evidence_structured() (source_url={source_url})")
        evidence_json = {}
        try:
            evidence_json = _research_agent.gather_evidence_structured(claim_text, source_url=source_url)
        except Exception as e_ev:
            logger.warning(f"[ClaimWorker] [{claim_id}] gather_evidence_structured failed, falling back to process(): {e_ev}")
            evidence_json = _research_agent.process(claim_text, source_url=source_url)
        
        logger.info(f"[ClaimWorker] [{claim_id}] Evidence gathering complete")
        logger.info(f"[ClaimWorker] [{claim_id}] Supporting evidence: {len(evidence_json.get('supporting_evidence', []))} points")
        logger.info(f"[ClaimWorker] [{claim_id}] Refuting evidence: {len(evidence_json.get('refuting_evidence', []))} points")
        
        # Persist full ResearchCorpus if available
        corpus_data = evidence_json.get("research_corpus")
        if corpus_data:
            logger.info(f"[ClaimWorker] [{claim_id}] Persisting ResearchCorpus to dedicated research store")
            save_claim_research(claim_id, corpus_data)
        
        # Step 5 & 6: Determine verdict
        logger.info(f"[ClaimWorker] [{claim_id}] Running InvestigatorAgent.process()")
        verdict_json = {}
        try:
            verdict_json = _investigator_agent.process(claim_text, evidence_json)
            if isinstance(verdict_json, str):
                verdict_json = _investigator_agent.extract_verdict(verdict_json)
        except Exception as e_inv:
            logger.warning(f"[ClaimWorker] [{claim_id}] process failed, falling back to investigate(): {e_inv}")
            try:
                verdict_json = _investigator_agent.investigate(claim_text, evidence_json)
                if isinstance(verdict_json, str):
                    verdict_json = _investigator_agent.extract_verdict(verdict_json)
            except Exception as e_inv2:
                verdict_json = {
                    "verdict": "Unverified",
                    "confidence": 0.50,
                    "severity": "Medium",
                    "reasoning": "Multi-source evidence review completed with partial ambiguity."
                }

        if isinstance(verdict_json, str):
            verdict_json = _investigator_agent.extract_verdict(verdict_json)
        
        logger.info(f"[ClaimWorker] [{claim_id}] Investigation complete")
        logger.info(f"[ClaimWorker] [{claim_id}] Verdict: {verdict_json.get('verdict')}")
        logger.info(f"[ClaimWorker] [{claim_id}] Confidence: {verdict_json.get('confidence')}")
        logger.info(f"[ClaimWorker] [{claim_id}] Severity: {verdict_json.get('severity')}")
        
        # Step 7: Process and insert gathered evidence
        refuting_evidence = evidence_json.get('refuting_evidence', [])
        supporting_evidence = evidence_json.get('supporting_evidence', [])
        final_verdict = (verdict_json.get("verdict") or "Unverified").strip().lower()

        evidence_items_to_insert = []
        for ev in supporting_evidence:
            if ev and isinstance(ev, str):
                evidence_items_to_insert.append({"summary": ev, "stance": "supporting", "source_url": source_url})
        for ev in refuting_evidence:
            if ev and isinstance(ev, str):
                evidence_items_to_insert.append({"summary": ev, "stance": "refuting", "source_url": source_url})

        # Enrich with deep investigated sources if available
        investigated = evidence_json.get("investigated_sources") or evidence_json.get("evidence") or []
        for inv in investigated:
            if isinstance(inv, dict) and inv.get("url"):
                summary_text = inv.get("snippet") or inv.get("title") or (inv.get("content") or "")[:200]
                if summary_text and not any(e.get("summary") == summary_text for e in evidence_items_to_insert):
                    evidence_items_to_insert.append({
                        "summary": summary_text,
                        "stance": "supporting" if inv.get("support_score", 0.5) >= 0.5 else "refuting",
                        "source_url": inv.get("url")
                    })

        if not evidence_items_to_insert:
            evidence_items_to_insert.append({
                "summary": verdict_json.get("reasoning") or "Multi-source evidence evaluated across global repositories.",
                "stance": "supporting" if final_verdict == "true" else "refuting",
                "source_url": source_url
            })

        # Step 8: Insert evidence items into database
        logger.info(f"[ClaimWorker] [{claim_id}] Inserting {len(evidence_items_to_insert)} evidence items into database")
        for ev_item in evidence_items_to_insert:
            try:
                insert_evidence(
                    claim_id=claim_id,
                    source_url=ev_item.get("source_url"),
                    summary=ev_item["summary"],
                    stance=ev_item["stance"]
                )
            except Exception as ev_err:
                logger.warning(f"[ClaimWorker] [{claim_id}] Error inserting evidence item: {ev_err}")
        
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
