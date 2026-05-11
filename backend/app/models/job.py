from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, HttpUrl, field_validator


class DetectionMode(str, Enum):
    AI = "ai"
    SIGNAL = "signal"
    HYBRID = "hybrid"


class OutputFormat(str, Enum):
    MP4 = "mp4"
    WEBM = "webm"


class JobStatus(str, Enum):
    PENDING = "pending"
    DOWNLOADING = "downloading"
    EXTRACTING = "extracting"
    TRANSCRIBING = "transcribing"
    ANALYZING = "analyzing"
    DONE = "done"
    FAILED = "failed"


class ProcessSettings(BaseModel):
    mode: DetectionMode = DetectionMode.HYBRID
    min_clip_duration: int = 10        # seconds
    max_clips: int = 10
    score_threshold: float = 0.35      # 0.0 – 1.0 (default lenient so clips usually appear)
    auto_trim_silence: bool = True
    output_format: OutputFormat = OutputFormat.MP4

    @field_validator("score_threshold")
    @classmethod
    def validate_threshold(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            raise ValueError("score_threshold must be between 0.0 and 1.0")
        return v

    @field_validator("min_clip_duration")
    @classmethod
    def validate_min_duration(cls, v: int) -> int:
        if v < 3:
            raise ValueError("min_clip_duration must be at least 3 seconds")
        return v


class JobCreate(BaseModel):
    url: str
    settings: ProcessSettings = ProcessSettings()

    @field_validator("url")
    @classmethod
    def validate_youtube_url(cls, v: str) -> str:
        if not any(domain in v for domain in ["youtube.com", "youtu.be"]):
            raise ValueError("Only YouTube URLs are supported")
        return v


class JobProgress(BaseModel):
    stage: str
    percent: int       # 0–100
    message: str


class JobResponse(BaseModel):
    job_id: str
    status: JobStatus
    progress: JobProgress
    created_at: datetime
    updated_at: datetime
    error: str | None = None
    video_title: str | None = None
    video_duration: int | None = None  # seconds
