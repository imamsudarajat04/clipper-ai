"""
Celery task — orchestrates the full video processing pipeline.
Stores job state in Redis so the SSE endpoint can stream progress.
"""
from __future__ import annotations

import json
import traceback
from datetime import datetime, timezone
from pathlib import Path

import redis as redis_lib

from app.core.celery_app import celery_app
from app.core.config import settings
from app.models.job import JobStatus
from app.pipeline.downloader import download_video, DownloadError
from app.pipeline.audio import extract_audio, AudioExtractError


# ---------------------------------------------------------------------------
# Redis helpers
# ---------------------------------------------------------------------------

def _redis() -> redis_lib.Redis:
    return redis_lib.from_url(settings.REDIS_URL, decode_responses=True)


def _job_key(job_id: str) -> str:
    return f"clipper:job:{job_id}"


def _update_job(
    r: redis_lib.Redis,
    job_id: str,
    *,
    status: JobStatus,
    stage: str,
    percent: int,
    message: str,
    extra: dict | None = None,
) -> None:
    data = {
        "job_id": job_id,
        "status": status.value,
        "stage": stage,
        "percent": percent,
        "message": message,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    if extra:
        data.update(extra)
    r.set(_job_key(job_id), json.dumps(data), ex=86400)


# ---------------------------------------------------------------------------
# Celery task
# ---------------------------------------------------------------------------

@celery_app.task(bind=True, name="app.tasks.pipeline_task.process_video")
def process_video(self, job_id: str, url: str, raw_settings: dict) -> dict:
    """
    Main pipeline task.

    Stages (Phase 1):
        1. Download video via yt-dlp          → 0–40%
        2. Extract audio via ffmpeg            → 40–60%
        3. (Stub) Transcribe / Analyze        → 60–90%
        4. Done                                → 100%
    """
    r = _redis()
    settings.ensure_dirs()

    def progress(status: JobStatus, stage: str, pct: int, msg: str, extra: dict | None = None):
        _update_job(r, job_id, status=status, stage=stage, percent=pct, message=msg, extra=extra)

    try:
        # ------------------------------------------------------------------ #
        # Stage 1 — Download
        # ------------------------------------------------------------------ #
        progress(JobStatus.DOWNLOADING, "download", 0, "Starting download…")

        def dl_cb(pct: int, msg: str):
            # Scale download to 0–40%
            progress(JobStatus.DOWNLOADING, "download", int(pct * 0.4), msg)

        dl_result = download_video(url, settings.VIDEOS_DIR, progress_cb=dl_cb)

        video_path: Path = dl_result["path"]
        progress(
            JobStatus.EXTRACTING,
            "extract",
            40,
            f"Downloaded: {dl_result['title']}",
            extra={
                "video_title": dl_result.get("title"),
                "video_duration": dl_result.get("duration"),
                "video_path": str(video_path),
            },
        )

        # ------------------------------------------------------------------ #
        # Stage 2 — Extract Audio
        # ------------------------------------------------------------------ #
        def audio_cb(pct: int, msg: str):
            # Scale audio extraction to 40–60%
            progress(JobStatus.EXTRACTING, "extract", 40 + int(pct * 0.2), msg)

        audio_path = extract_audio(video_path, settings.AUDIO_DIR, progress_cb=audio_cb)

        progress(
            JobStatus.TRANSCRIBING,
            "transcribe",
            60,
            "Audio ready — queued for analysis",
            extra={"audio_path": str(audio_path)},
        )

        # ------------------------------------------------------------------ #
        # Stage 3 — AI / Signal analysis (Phase 2 stub)
        # ------------------------------------------------------------------ #
        detection_mode = raw_settings.get("mode", "hybrid")
        progress(
            JobStatus.ANALYZING,
            "analyze",
            70,
            f"Analysis mode: {detection_mode} (Phase 2 — stub)",
        )

        # Placeholder clips result for Phase 1
        clips_data: list[dict] = []

        # ------------------------------------------------------------------ #
        # Stage 4 — Done
        # ------------------------------------------------------------------ #
        progress(
            JobStatus.DONE,
            "done",
            100,
            "Pipeline complete",
            extra={"clips": clips_data},
        )

        return {"job_id": job_id, "status": "done"}

    except (DownloadError, AudioExtractError) as exc:
        progress(JobStatus.FAILED, "error", 0, str(exc))
        raise

    except Exception as exc:
        tb = traceback.format_exc()
        progress(JobStatus.FAILED, "error", 0, f"Unexpected error: {exc}")
        raise RuntimeError(f"Pipeline failed:\n{tb}") from exc
