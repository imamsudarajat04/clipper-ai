from __future__ import annotations

import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    APP_NAME: str = "Clipper AI"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    ALLOWED_ORIGINS: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    # Redis / Celery
    REDIS_URL: str = "redis://localhost:6379/0"

    # Storage
    OUTPUT_DIR: Path = Path("../data")

    # yt-dlp — Netscape cookies.txt when YouTube returns "Sign in to confirm you're not a bot"
    # Docker example: /data/youtube_cookies.txt (file on host under ./data/)
    YTDLP_COOKIES_FILE: str = ""

    @property
    def VIDEOS_DIR(self) -> Path:
        return self.OUTPUT_DIR / "videos"

    @property
    def AUDIO_DIR(self) -> Path:
        return self.OUTPUT_DIR / "audio"

    @property
    def CLIPS_DIR(self) -> Path:
        return self.OUTPUT_DIR / "clips"

    # AI (Phase 2)
    GROQ_API_KEY: str = ""
    # llama-3.1-8b-instant = 6K TPM (easy to exceed with long transcripts). llama-3.3-70b-versatile = 12K TPM.
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    WHISPER_MODEL: str = "base"
    # Hard cap on transcript chars sent to Groq (full prompt must stay under model TPM/RPM limits).
    GROQ_TRANSCRIPT_MAX_CHARS: int = 3800

    # Signal detection (Phase 2)
    SIGNAL_WINDOW_MS: int = 1000
    SIGNAL_RMS_PERCENTILE: float = 0.60  # windows above this energy quantile become candidates
    SCENE_DIFF_THRESHOLD: float = 28.0  # mean abs diff on 160px gray (tuned for 0–255)
    SCENE_MIN_INTERVAL_S: float = 1.5

    # Pipeline defaults
    MAX_VIDEO_DURATION_SECONDS: int = 3600  # 1 hour
    DEFAULT_MIN_CLIP_DURATION: int = 10
    DEFAULT_MAX_CLIPS: int = 10
    DEFAULT_SCORE_THRESHOLD: float = 0.5

    def ensure_dirs(self) -> None:
        for d in [self.VIDEOS_DIR, self.AUDIO_DIR, self.CLIPS_DIR]:
            d.mkdir(parents=True, exist_ok=True)


settings = Settings()
