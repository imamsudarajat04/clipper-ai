"""
ffmpeg audio extractor.
Converts a video file to a 16 kHz mono WAV — optimal for Whisper transcription.
"""
from __future__ import annotations

from pathlib import Path
from typing import Callable

import ffmpeg


class AudioExtractError(Exception):
    pass


def extract_audio(
    video_path: Path,
    output_dir: Path,
    progress_cb: Callable[[int, str], None] | None = None,
) -> Path:
    """
    Extract audio track from a video file.

    Args:
        video_path: Path to the source video (.mp4, .mkv, etc.)
        output_dir: Directory to write the .wav file
        progress_cb: Optional callback(percent: int, message: str)

    Returns:
        Path to the output .wav file
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    wav_path = output_dir / (video_path.stem + ".wav")

    if progress_cb:
        progress_cb(0, "Extracting audio…")

    try:
        (
            ffmpeg
            .input(str(video_path))
            .output(
                str(wav_path),
                ac=1,          # mono
                ar=16000,      # 16 kHz
                acodec="pcm_s16le",
                vn=None,       # no video
            )
            .overwrite_output()
            .run(quiet=True, capture_stdout=True, capture_stderr=True)
        )
    except ffmpeg.Error as exc:
        stderr = exc.stderr.decode("utf-8", errors="replace") if exc.stderr else ""
        raise AudioExtractError(f"ffmpeg failed: {stderr}") from exc

    if not wav_path.exists():
        raise AudioExtractError(f"Expected output file not found: {wav_path}")

    if progress_cb:
        progress_cb(100, f"Audio extracted → {wav_path.name}")

    return wav_path
