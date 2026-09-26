"""
Aegis Protocol — Research Replay & Dossier API Router
======================================================
Exposes endpoints for forensic provenance inspection, immutable research dossiers (R-2026-XXXX),
and deterministic investigation replay.
"""

import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from backend.services.research.replay_ledger import replay_ledger

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/replay", tags=["Research Provenance & Replay"])


@router.get("/dossiers", summary="List Recent Research Dossiers")
async def list_recent_dossiers(limit: int = Query(15, ge=1, le=50)):
    """List recently completed investigations with immutable session IDs."""
    try:
        return {
            "status": "success",
            "count": len(replay_ledger.list_recent_dossiers(limit=limit)),
            "dossiers": replay_ledger.list_recent_dossiers(limit=limit),
        }
    except Exception as e:
        logger.error(f"[API] Failed listing dossiers: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dossiers/{session_id}", summary="Get Full Research Dossier")
async def get_research_dossier(session_id: str):
    """Retrieve complete evidence hashes, decision ledger, and lineage DAG for a research ID."""
    clean_id = session_id.strip()
    dossier = replay_ledger.get_dossier(clean_id)
    if not dossier:
        raise HTTPException(status_code=404, detail=f"Research dossier '{clean_id}' not found.")
    return {
        "status": "success",
        "dossier": dossier,
    }


@router.post("/reexecute/{session_id}", summary="Replay Investigation Trace")
async def replay_investigation(session_id: str):
    """
    Reruns the deterministic playback of an investigation.
    Validates candidate content hashes, checks decision criteria, and verifies reproduction.
    """
    clean_id = session_id.strip()
    replay_res = replay_ledger.replay_investigation(clean_id)
    if replay_res.get("status") == "error":
        raise HTTPException(status_code=404, detail=replay_res.get("error"))
    return replay_res
