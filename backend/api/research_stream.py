"""Ephemeral live observation, not a persistent/resumable job queue.

Disconnects/deadlines stop observation, NOT blocking provider threads. Normal
per-agent admission stays held until its actual worker finishes.
"""

import asyncio
import json
import logging
import time
import uuid

from fastapi import HTTPException
from fastapi.encoders import jsonable_encoder
from starlette.responses import StreamingResponse

from backend.application.research.progress import progress_observer

logger = logging.getLogger(__name__)
STREAM_TIMEOUT_SECONDS = 240
HEARTBEAT_SECONDS = 5
_running = set()


class EventStreamResponse(StreamingResponse):
    media_type = "text/event-stream"


def analysis_stream(agent, callback, admission_lock):
    # Fast precheck; _run_bounded_scan remains the atomic admission owner.
    if admission_lock.locked():
        raise HTTPException(429, "Agent is handling another scan; retry shortly", headers={"Retry-After": "3"})
    analysis_id = str(uuid.uuid4())
    loop = asyncio.get_running_loop()
    started = time.monotonic()
    queue = asyncio.Queue(maxsize=64)
    observing = True

    def enqueue(event, data):
        if not observing:
            return
        if queue.full():
            queue.get_nowait()
        queue.put_nowait((event, data))

    def observe(data):
        event = {**data, "analysis_id": analysis_id,
                 "elapsed_seconds": round(time.monotonic() - started, 2)}
        try:
            loop.call_soon_threadsafe(enqueue, "progress", event)
        except RuntimeError:
            pass

    async def run():
        token = progress_observer.set(observe)
        try:
            observe({"phase": "accepted", "completed": 0, "total": 3})
            logger.info("[Analysis] id=%s agent=%s started", analysis_id, agent)
            result = jsonable_encoder(await callback())
            json.dumps(result, allow_nan=False)  # Fail inside the guarded task, not mid-stream.
            enqueue("result", {"analysis_id": analysis_id, "completed": 3, "total": 3, "result": result})
            logger.info("[Analysis] id=%s agent=%s completed elapsed_s=%.2f", analysis_id, agent, time.monotonic() - started)
        except Exception as error:
            code = error.status_code if isinstance(error, HTTPException) else 500
            enqueue("error", {"analysis_id": analysis_id, "status": code,
                              "message": "Agent is busy; wait before retrying." if code == 429 else "Research failed; no completed result is claimed."})
            logger.warning("[Analysis] id=%s agent=%s failed type=%s status=%s", analysis_id, agent, type(error).__name__, code)
        finally:
            progress_observer.reset(token)

    # Retain job on client disconnect: cancelling to_thread would release the
    # observer but not stop the actual mutable worker. No unsafe early unlock.
    task = asyncio.create_task(run())
    _running.add(task)
    task.add_done_callback(_running.discard)

    async def events():
        nonlocal observing
        try:
            while True:
                remaining = STREAM_TIMEOUT_SECONDS - (time.monotonic() - started)
                if remaining <= 0:
                    yield encode("error", {"analysis_id": analysis_id, "status": 504,
                                          "message": "Observation deadline reached. Server work may still continue; do not repeatedly retry."})
                    break
                try:
                    event, data = await asyncio.wait_for(queue.get(), timeout=min(HEARTBEAT_SECONDS, remaining))
                except asyncio.TimeoutError:
                    event, data = "heartbeat", {"analysis_id": analysis_id,
                                               "elapsed_seconds": round(time.monotonic() - started, 2)}
                yield encode(event, data)
                if event in {"result", "error"}:
                    break
        finally:
            observing = False

    return EventStreamResponse(events(), headers={
        "Cache-Control": "no-cache, no-store, no-transform", "X-Accel-Buffering": "no",
        "X-Analysis-ID": analysis_id,
    })


def encode(event, data):
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=True)}\n\n"
