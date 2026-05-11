"""
POST /api/process — accept YouTube URL + settings, enqueue Celery task.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

import redis as redis_lib
from fastapi import APIRouter, HTTPException
from kombu.exceptions import OperationalError

from app.core.config import settings
from app.models.job import JobCreate, JobResponse, JobStatus, JobProgress
from app.tasks.pipeline_task import process_video

router = APIRouter()


def _redis() -> redis_lib.Redis:
    return redis_lib.from_url(settings.REDIS_URL, decode_responses=True)


@router.post("/process", response_model=JobResponse, status_code=202)
async def submit_process(payload: JobCreate) -> JobResponse:
    """
    Submit a YouTube URL for highlight detection.

    Returns a job_id that can be polled via GET /api/job/{id}.
    """
    job_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    initial_state = {
        "job_id": job_id,
        "status": JobStatus.PENDING.value,
        "stage": "queued",
        "percent": 0,
        "message": "Job queued, waiting for worker…",
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
        "url": payload.url,
        "settings": payload.settings.model_dump(),
    }

    r = _redis()
    try:
        r.set(f"clipper:job:{job_id}", json.dumps(initial_state), ex=86400)
    except redis_lib.RedisError as exc:
        raise HTTPException(status_code=503, detail=f"Redis unavailable: {exc}") from exc

    # Enqueue Celery task (broker failures are not redis_lib.RedisError)
    try:
        process_video.apply_async(
            args=[job_id, payload.url, payload.settings.model_dump()],
            task_id=job_id,
            queue="pipeline",
        )
    except OperationalError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Task queue unavailable — check Redis and the Celery worker. {exc}",
        ) from exc

    return JobResponse(
        job_id=job_id,
        status=JobStatus.PENDING,
        progress=JobProgress(stage="queued", percent=0, message="Job queued"),
        created_at=now,
        updated_at=now,
    )
