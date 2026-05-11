"""
Local Whisper transcription (openai-whisper).
"""
from __future__ import annotations

import logging
from pathlib import Path

import whisper

from app.core.config import settings
from app.pipeline.detect_types import TranscriptSegment

logger = logging.getLogger(__name__)


class WhisperTranscribeError(Exception):
    pass


_model: whisper.Whisper | None = None


def _load_model() -> whisper.Whisper:
    global _model
    if _model is None:
        name = (settings.WHISPER_MODEL or "base").strip().lower()
        logger.info("Loading Whisper model %r (first run may download weights)", name)
        _model = whisper.load_model(name)
    return _model


def transcribe_wav(wav_path: Path) -> list[TranscriptSegment]:
    """
    Transcribe a 16 kHz mono WAV into timestamped segments.

    Returns:
        List of ``TranscriptSegment`` with ``start``, ``end``, ``text``.
    """
    path = wav_path.resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Audio not found: {path}")

    model = _load_model()
    logger.info("Whisper transcribe start: %s", path)
    try:
        result = model.transcribe(
            str(path),
            fp16=False,
            word_timestamps=False,
            verbose=False,
        )
    except Exception as exc:
        logger.exception("Whisper transcribe failed")
        raise WhisperTranscribeError(f"Whisper transcription failed: {exc}") from exc

    segments: list[TranscriptSegment] = []
    for seg in result.get("segments") or []:
        try:
            start = float(seg.get("start", 0.0))
            end = float(seg.get("end", start))
            text = (seg.get("text") or "").strip()
            if end <= start or not text:
                continue
            segments.append(TranscriptSegment(start=start, end=end, text=text))
        except (TypeError, ValueError) as exc:
            logger.warning("Skipping malformed Whisper segment: %s (%s)", seg, exc)
            continue

    logger.info("Whisper transcribe done: %d segments", len(segments))
    return segments


def segments_to_prompt_text(
    segments: list[TranscriptSegment],
    max_chars: int | None = None,
) -> str:
    """
    Build a transcript with timestamps for Groq, staying under ``GROQ_TRANSCRIPT_MAX_CHARS``.

    Long videos: increase stride (sample every Nth segment) so early and late dialogue
    still appear instead of only the first minutes.
    """
    cap = int(max_chars if max_chars is not None else settings.GROQ_TRANSCRIPT_MAX_CHARS)
    if not segments:
        return ""

    reserve = 120  # room for truncation notice line
    best: str | None = None

    stride = 1
    while stride <= len(segments):
        sample = segments[::stride]
        lines: list[str] = []
        used = 0
        for s in sample:
            line = f"[{s.start:.1f}s–{s.end:.1f}s] {s.text}"
            if used + len(line) + 1 > cap - reserve:
                lines.append(
                    f"… [+{max(0, len(segments) - len(sample))} segments omitted; "
                    f"stride={stride} sample for API size]"
                )
                break
            lines.append(line)
            used += len(line) + 1
        text = "\n".join(lines)
        if len(text) <= cap:
            if stride > 1:
                logger.info(
                    "Groq transcript: stride=%d segments=%d/%d chars=%d (cap=%d)",
                    stride,
                    len(sample),
                    len(segments),
                    len(text),
                    cap,
                )
            return text
        best = text
        if stride >= len(segments):
            break
        stride = min(len(segments), max(stride * 2, stride + 1))

    logger.warning("Transcript still exceeds cap=%d after striding; hard-truncating", cap)
    return (best or "")[:cap] + "\n… [truncated]"
