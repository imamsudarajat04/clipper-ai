"""
Stub modules for Phase 2 pipeline stages.
These will be fully implemented in Phase 2.
"""
from __future__ import annotations
from pathlib import Path
from typing import Callable


class TranscriptionResult:
    segments: list[dict]
    full_text: str

    def __init__(self, segments: list[dict], full_text: str):
        self.segments = segments
        self.full_text = full_text


def transcribe_audio(
    audio_path: Path,
    model_name: str = "base",
    progress_cb: Callable[[int, str], None] | None = None,
) -> TranscriptionResult:
    """Phase 2: Whisper transcription — stub."""
    raise NotImplementedError("Transcription will be implemented in Phase 2")
