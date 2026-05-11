from __future__ import annotations

from pydantic import BaseModel


class ClipResult(BaseModel):
    index: int
    start_time: float          # seconds
    end_time: float            # seconds
    duration: float            # seconds
    confidence_score: float    # 0.0 – 1.0
    summary: str | None = None
    keywords: list[str] = []
    clip_filename: str | None = None
    clip_url: str | None = None
    thumbnail_url: str | None = None
    detection_source: str = "unknown"  # "ai", "signal", "hybrid"
    clip_id: str | None = None
    reason: str | None = None


class ClipsResponse(BaseModel):
    job_id: str
    total: int
    detection_mode: str
    clips: list[ClipResult]
    video_title: str | None = None
    video_duration: float | None = None  # seconds
    processed_at: str | None = None
