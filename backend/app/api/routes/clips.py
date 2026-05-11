"""
GET /api/clips/{job_id} — return detected highlight clips for a completed job.
"""
from __future__ import annotations

import json

import redis.asyncio as aioredis
from fastapi import APIRouter, HTTPException

from app.core.config import settings
from app.models.clip import ClipsResponse

router = APIRouter()


@router.get("/clips/{job_id}", response_model=ClipsResponse)
async def get_clips(job_id: str) -> ClipsResponse:
    """
    Return the list of highlight clips produced by the pipeline.
    Job must be in 'done' status.
    """
    r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    try:
        raw = await r.get(f"clipper:job:{job_id}")
    finally:
        await r.aclose()

    if raw is None:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")

    data = json.loads(raw)
    status = data.get("status")

    if status == "failed":
        raise HTTPException(
            status_code=422,
            detail=data.get("message") or "Pipeline failed",
        )

    if status != "done":
        raise HTTPException(
            status_code=409,
            detail=f"Job is not completed yet (status={status})",
        )

    clips = data.get("clips", [])

    return ClipsResponse(
        job_id=job_id,
        total=len(clips),
        detection_mode=data.get("detection_mode")
        or data.get("settings", {}).get("mode", "hybrid"),
        clips=clips,
        video_title=data.get("video_title"),
        video_duration=data.get("video_duration"),
        processed_at=data.get("updated_at"),
    )
