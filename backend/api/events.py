"""
Aegis Protocol — Monitoring Events API Router
=============================================
Exposes secure webhook endpoints for external monitoring agents (e.g. Huginn)
and allows Aegis intelligence agents to inspect retained continuous feeds.
"""

import json
from typing import Optional
from fastapi import APIRouter, Header, HTTPException, Query, Request
from starlette.concurrency import run_in_threadpool
from backend.infrastructure.acquisition.adapters.events.huginn import (
    huginn_ingestor,
    MAX_HUGINN_PAYLOAD_BYTES,
)

router = APIRouter(prefix="/api/events", tags=["events"])


@router.post("/huginn")
async def receive_huginn_event(
    request: Request,
    x_huginn_secret: Optional[str] = Header(None, alias="X-Huginn-Secret"),
    authorization: Optional[str] = Header(None),
):
    """
    Secure webhook endpoint for incoming Huginn monitoring events.
    Verifies authentication secret before accepting payloads into the raw event pool.
    """
    secret = x_huginn_secret or authorization
    # Authenticate before reading a potentially large/unbounded request body.
    if not huginn_ingestor.verify_auth(secret):
        raise HTTPException(status_code=401, detail="Invalid or missing Huginn webhook secret")
    length = request.headers.get("content-length")
    if length is not None:
        try:
            if not 0 <= int(length) <= MAX_HUGINN_PAYLOAD_BYTES:
                raise HTTPException(status_code=413, detail="Monitoring payload too large")
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid content length")
    if request.headers.get("content-type", "").split(";", 1)[0].lower() != "application/json":
        raise HTTPException(status_code=415, detail="JSON content type required")
    raw = bytearray()
    async for chunk in request.stream():
        if len(raw) + len(chunk) > MAX_HUGINN_PAYLOAD_BYTES:
            raise HTTPException(status_code=413, detail="Monitoring payload too large")
        raw.extend(chunk)
    try:
        payload = json.loads(raw)
    except (ValueError, UnicodeError, RecursionError):
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Payload must be a JSON object")

    # DNS validation, locks and durable SQLite operations must not block ASGI.
    result = await run_in_threadpool(huginn_ingestor.ingest, payload, auth_secret=secret)

    if result.get("status") == "rejected":
        reason = result.get("reason")
        status_code = (401 if reason == "AUTHENTICATION_FAILED" else
                       409 if reason == "EVENT_ID_CONFLICT" else
                       503 if reason == "PERSISTENCE_FAILED" else 400)
        raise HTTPException(status_code=status_code, detail=result.get("message"))

    return result


@router.get("/huginn")
def list_huginn_events(
    agent_target: Optional[str] = Query(None, description="Filter by target agent (scout, brandshield, trending, personal_watch)"),
    target_entity: Optional[str] = Query(None, description="Filter by monitored target entity"),
    limit: int = Query(50, ge=1, le=200),
    x_huginn_secret: Optional[str] = Header(None, alias="X-Huginn-Secret"),
    authorization: Optional[str] = Header(None),
):
    """
    Query retained monitoring events from background streams.
    Used by Scout, BrandShield, Trending, and Personal Watch during investigation planning.
    """
    if not huginn_ingestor.verify_auth(x_huginn_secret or authorization):
        raise HTTPException(status_code=401, detail="Invalid or missing Huginn webhook secret")
    events = huginn_ingestor.get_events(
        agent_target=agent_target,
        target_entity=target_entity,
        limit=limit,
    )
    return {
        "status": "success",
        "count": len(events),
        "events": [e.to_dict() for e in events],
    }
