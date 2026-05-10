"""
GET /api/job/{job_id}        — polling endpoint (JSON)
GET /api/job/{job_id}/stream — SSE real-time progress stream
"""
from __future__ import annotations

import asyncio
import json

import redis.asyncio as aioredis
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.core.config import settings

router = APIRouter()


def _job_key(job_id: str) -> str:
    return f"clipper:job:{job_id}"


async def _get_raw(job_id: str) -> dict:
    r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    try:
        raw = await r.get(_job_key(job_id))
    finally:
        await r.aclose()

    if raw is None:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")
    return json.loads(raw)


@router.get("/job/{job_id}")
async def get_job_status(job_id: str) -> dict:
    """Return the current job state as JSON (for polling)."""
    return await _get_raw(job_id)


@router.get("/job/{job_id}/stream")
async def stream_job_progress(job_id: str) -> StreamingResponse:
    """
    Server-Sent Events stream.
    Emits a 'progress' event every 500 ms until the job is done or failed.
    """

    async def _event_generator():
        r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        try:
            terminal_statuses = {"done", "failed"}
            last_payload: str | None = None

            while True:
                raw = await r.get(_job_key(job_id))

                if raw is None:
                    yield f"event: error\ndata: {json.dumps({'message': 'Job not found'})}\n\n"
                    break

                # Only emit when state changes (save bandwidth)
                if raw != last_payload:
                    last_payload = raw
                    data = json.loads(raw)
                    yield f"event: progress\ndata: {json.dumps(data)}\n\n"

                    if data.get("status") in terminal_statuses:
                        yield "event: done\ndata: {}\n\n"
                        break

                await asyncio.sleep(0.5)
        finally:
            await r.aclose()

    return StreamingResponse(
        _event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
