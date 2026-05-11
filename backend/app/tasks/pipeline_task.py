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

# Pipeline modules are imported inside ``process_video`` so the FastAPI app (which
# imports this module for ``apply_async``) does not load Whisper/OpenCV/etc. at
# startup — avoids crashes when bind-mounted files are mid-save during --reload.


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
    """Merge into existing Redis job document (preserves url, settings, created_at, etc.)."""
    key = _job_key(job_id)
    raw = r.get(key)
    base: dict = json.loads(raw) if raw else {}
    base.update(
        {
            "job_id": job_id,
            "status": status.value,
            "stage": stage,
            "percent": percent,
            "message": message,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    if extra:
        base.update(extra)
    r.set(key, json.dumps(base), ex=86400)


# ---------------------------------------------------------------------------
# Celery task
# ---------------------------------------------------------------------------

@celery_app.task(bind=True, name="app.tasks.pipeline_task.process_video")
def process_video(self, job_id: str, url: str, raw_settings: dict) -> dict:
    """
    Full pipeline: download → extract audio → detect (ai / signal / hybrid) → export clips.
    """
    from app.pipeline.audio import AudioExtractError, extract_audio
    from app.pipeline.clip_export import ClipExportError, export_clip
    from app.pipeline.downloader import DownloadError, download_video
    from app.pipeline.groq_highlights import GroqHighlightError
    from app.pipeline.hybrid_engine import run_detection
    from app.pipeline.transcribe_whisper import WhisperTranscribeError

    r = _redis()
    settings.ensure_dirs()

    def progress(status: JobStatus, stage: str, pct: int, msg: str, extra: dict | None = None):
        _update_job(r, job_id, status=status, stage=stage, percent=pct, message=msg, extra=extra)

    mode = str(raw_settings.get("mode", "hybrid")).lower().strip()
    max_clips = int(raw_settings.get("max_clips", settings.DEFAULT_MAX_CLIPS))
    min_clip_duration = int(raw_settings.get("min_clip_duration", settings.DEFAULT_MIN_CLIP_DURATION))
    score_threshold = float(raw_settings.get("score_threshold", settings.DEFAULT_SCORE_THRESHOLD))
    output_format = str(raw_settings.get("output_format", "mp4")).lower().strip()

    try:
        # ------------------------------------------------------------------ #
        # Stage 1 — Download
        # ------------------------------------------------------------------ #
        progress(JobStatus.DOWNLOADING, "download", 0, "Starting download…")

        def dl_cb(pct: int, msg: str):
            progress(JobStatus.DOWNLOADING, "download", int(pct * 0.35), msg)

        dl_result = download_video(url, settings.VIDEOS_DIR, progress_cb=dl_cb)

        video_path: Path = dl_result["path"]
        video_title = str(dl_result.get("title") or "")
        video_duration = dl_result.get("duration")
        if isinstance(video_duration, (int, float)):
            vd: float | None = float(video_duration)
        else:
            vd = None

        progress(
            JobStatus.EXTRACTING,
            "extract",
            36,
            f"Downloaded: {video_title}",
            extra={
                "video_title": video_title or None,
                "video_duration": video_duration,
                "video_path": str(video_path),
            },
        )

        # ------------------------------------------------------------------ #
        # Stage 2 — Extract Audio
        # ------------------------------------------------------------------ #
        def audio_cb(pct: int, msg: str):
            progress(JobStatus.EXTRACTING, "extract", 36 + int(pct * 0.13), msg)

        audio_path = extract_audio(video_path, settings.AUDIO_DIR, progress_cb=audio_cb)

        progress(
            JobStatus.TRANSCRIBING,
            "transcribe",
            50,
            f"Detection mode: {mode} — running models…",
            extra={"audio_path": str(audio_path)},
        )

        # ------------------------------------------------------------------ #
        # Stage 3 — Detection (Whisper + Groq and/or signal)
        # ------------------------------------------------------------------ #
        clips = run_detection(
            mode,
            audio_path,
            video_path,
            video_title=video_title or None,
            max_clips=max_clips,
            min_clip_duration=min_clip_duration,
            score_threshold=score_threshold,
            video_duration=vd,
        )

        progress(
            JobStatus.ANALYZING,
            "analyze",
            72,
            f"Found {len(clips)} highlight(s); exporting clips…",
        )

        # ------------------------------------------------------------------ #
        # Stage 4 — Export clips (ffmpeg)
        # ------------------------------------------------------------------ #
        clips_data: list[dict] = []
        n = len(clips)
        for i, c in enumerate(clips):
            clip_id = f"clip_{i + 1:03d}"
            out_name = f"{job_id}_{clip_id}.{output_format if output_format in ('mp4', 'webm') else 'mp4'}"
            out_path = settings.CLIPS_DIR / out_name
            export_clip(
                video_path,
                c.start,
                c.end,
                out_path,
                output_format=output_format,
            )
            dur = max(0.0, c.end - c.start)
            pct = 72 + int(26 * (i + 1) / max(1, n))
            progress(
                JobStatus.ANALYZING,
                "analyze",
                min(98, pct),
                f"Exported {clip_id} ({i + 1}/{n})",
            )
            clips_data.append(
                {
                    "index": i,
                    "clip_id": clip_id,
                    "start_time": c.start,
                    "end_time": c.end,
                    "duration": dur,
                    "confidence_score": round(c.score, 4),
                    "summary": c.reason[:500] if c.reason else None,
                    "reason": c.reason,
                    "keywords": [],
                    "clip_filename": out_path.name,
                    "clip_url": None,
                    "thumbnail_url": None,
                    "detection_source": c.source,
                }
            )

        # ------------------------------------------------------------------ #
        # Stage 5 — Done
        # ------------------------------------------------------------------ #
        progress(
            JobStatus.DONE,
            "done",
            100,
            "Pipeline complete",
            extra={
                "clips": clips_data,
                "detection_mode": mode,
            },
        )

        return {"job_id": job_id, "status": "done", "clips": len(clips_data)}

    except (
        DownloadError,
        AudioExtractError,
        GroqHighlightError,
        WhisperTranscribeError,
        ClipExportError,
    ) as exc:
        progress(JobStatus.FAILED, "error", 0, str(exc))
        raise

    except Exception as exc:
        tb = traceback.format_exc()
        progress(JobStatus.FAILED, "error", 0, f"Unexpected error: {exc}")
        raise RuntimeError(f"Pipeline failed:\n{tb}") from exc
