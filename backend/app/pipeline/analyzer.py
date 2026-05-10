"""
Stub modules for Phase 2 pipeline stages.
"""
from __future__ import annotations
from pathlib import Path
from typing import Callable


def analyze_with_llm(
    transcript_segments: list[dict],
    settings: dict,
    progress_cb: Callable[[int, str], None] | None = None,
) -> list[dict]:
    """Phase 2: Groq LLM analysis — stub."""
    raise NotImplementedError("LLM analysis will be implemented in Phase 2")


def detect_signals(
    video_path: Path,
    audio_path: Path,
    settings: dict,
    progress_cb: Callable[[int, str], None] | None = None,
) -> list[dict]:
    """Phase 2: OpenCV + PyDub signal detection — stub."""
    raise NotImplementedError("Signal detection will be implemented in Phase 2")
