"""
Aegis Protocol — Threat Intelligence Lab Router
================================================
Exposes deterministic forensic and statistical physics instruments:
1. Zipf-Mandelbrot Token-Rank Power-Law Regression
2. Hawkes Self-Exciting Point Process Contagion Simulator
3. 3-Node Byzantine Fault-Tolerant Consensus Arbitrament
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from backend.services.threat_instruments import (
    compute_mandelbrot_fit,
    simulate_hawkes_contagion,
    arbitrate_ensemble_consensus,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Threat Intelligence Lab"])


# ── Request Models ───────────────────────────────────────────────────────────

class SyntheticDetectRequest(BaseModel):
    text: Optional[str] = Field(
        None,
        description="Text sample to test with Mandelbrot rank-frequency regression.",
        json_schema_extra={"example": "The implementation of distributed consensus protocols in decentralized architectures demonstrates significant advancements in fault-tolerant computing paradigms."}
    )
    claim: Optional[str] = Field(None, description="Alternative field for claim text.")


class BlastRadiusRequest(BaseModel):
    topic: Optional[str] = Field(
        "Global Cloud Infrastructure",
        description="Epicenter topic or entity.",
        json_schema_extra={"example": "Global Cloud Infrastructure"}
    )
    claim: Optional[str] = Field(
        "Massive zero-day exploit crippling tier-1 data centers worldwide",
        description="Viral claim text to simulate.",
        json_schema_extra={"example": "Massive zero-day exploit crippling tier-1 data centers worldwide"}
    )
    duration_hours: Optional[int] = Field(24, ge=1, le=48, description="Simulation window in hours.")


class ConsensusRequest(BaseModel):
    claim: str = Field(
        ...,
        description="Claim to arbitrate via 3-node Byzantine Fault-Tolerant consensus.",
        json_schema_extra={"example": "5G telecommunication towers cause cellular oxygen deprivation and viral mutations."}
    )


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.post(
    "/api/lab/synthetic-detect",
    summary="Mandelbrot Token-Rank Power-Law Regression"
)
@router.post("/lab/synthetic-detect")
@router.post("/api/threat-lab/mandelbrot-fit")
async def lab_synthetic_detect(req: SyntheticDetectRequest):
    """Evaluate Zipf-Mandelbrot power-law fit on text tokens."""
    text = (req.text or req.claim or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="Text or claim cannot be empty.")

    res = compute_mandelbrot_fit(text)
    return JSONResponse(res)


@router.post(
    "/api/lab/blast-radius",
    summary="Hawkes Self-Exciting Point Process Contagion Simulation"
)
@router.post("/lab/blast-radius")
@router.post("/api/threat-lab/hawkes-sim")
async def lab_blast_radius(req: BlastRadiusRequest):
    """Simulate viral cascade and contagion reproduction number R_0."""
    topic = (req.topic or "").strip()
    claim = (req.claim or "").strip()
    if not topic and not claim:
        raise HTTPException(status_code=400, detail="Topic or claim is required.")

    try:
        res = simulate_hawkes_contagion(topic=topic, claim=claim, horizon_hours=req.duration_hours or 24)
        return JSONResponse(res)
    except Exception as e:
        logger.error(f"[Hawkes Simulation] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/api/lab/consensus",
    summary="3-Node Byzantine Fault-Tolerant Consensus Arbitrament"
)
@router.post("/lab/consensus")
@router.post("/api/byzantine/arbitrate")
async def lab_consensus(req: ConsensusRequest):
    """Arbitrate multi-node consensus across independent evaluators with outlier pruning."""
    claim = (req.claim or "").strip()
    if not claim:
        raise HTTPException(status_code=400, detail="Claim is required.")

    # Fixed educational inputs illustrate aggregation; no source investigation occurs.
    agent_results = [
        {"id": "node-a", "name": "Example A", "verdict": "TRUE", "confidence": 80,
         "reasoning": "Illustrative input score, not a researched assessment."},
        {"id": "node-b", "name": "Example B", "verdict": "TRUE", "confidence": 75,
         "reasoning": "Illustrative input score, not independent corroboration."},
        {"id": "node-c", "name": "Example C", "verdict": "FALSE", "confidence": 40,
         "reasoning": "Illustrative disagreeing input for the aggregation exercise."},
    ]
    arb_res = arbitrate_ensemble_consensus(agent_results)
    annotated_nodes = arb_res.get("nodes", agent_results)
    outlier_agent = next((a for a in annotated_nodes if a.get("is_outlier")), annotated_nodes[0] if annotated_nodes else {"id": "none", "name": "None"})

    valid_agents = [a for a in annotated_nodes if not a.get("is_outlier")]
    if not valid_agents:
        valid_agents = annotated_nodes

    consensus_verdict = arb_res.get("consensus_verdict", "UNVERIFIED")
    agreeing = [a["confidence"] for a in valid_agents if a.get("verdict") == consensus_verdict]
    consensus_confidence = round(sum(agreeing) / len(agreeing), 1) if agreeing else arb_res.get("mean_confidence", 80.0)

    return JSONResponse({
        "status": "success", "is_simulation": True, "verdict_scope": "NOT_A_FACT_CHECK",
        "claim": claim,
        "agents": annotated_nodes,
        "outlier_pruned_id": outlier_agent.get("id"),
        "outlier_pruned_name": outlier_agent.get("name"),
        "w_msr_status": f"Outlier identification complete via {arb_res.get('fault_tolerance_model')}.",
        "consensus_verdict": consensus_verdict,
        "consensus_confidence": consensus_confidence,
        "quorum_reached": arb_res.get("consensus_reached", True),
        "quorum_ratio": arb_res.get("quorum_ratio", 1.0),
        "epistemic_synthesis": "Fixed example scores demonstrate agreement and outlier handling. No sources were checked and this result does not assess the entered claim."

    })
