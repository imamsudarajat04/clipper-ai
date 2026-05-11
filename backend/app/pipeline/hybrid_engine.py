"""
Phase 2 detection orchestration: AI (Whisper + Groq), signal, or hybrid.
"""
from __future__ import annotations

import logging
from pathlib import Path

from app.pipeline.detect_types import (
    HighlightCandidate,
    TranscriptSegment,
    merge_intervals,
    overlap_seconds,
    enforce_min_duration,
)
from app.pipeline.groq_highlights import analyze_highlights_groq
from app.pipeline.signal_detect import run_signal_detection
from app.pipeline.transcribe_whisper import segments_to_prompt_text, transcribe_wav

logger = logging.getLogger(__name__)


def _fallback_highlights_from_transcript(
    segments: list[TranscriptSegment],
    *,
    max_clips: int,
    target_seconds: float = 22.0,
) -> list[HighlightCandidate]:
    """
    If the LLM returns nothing, build coarse windows from Whisper segments so the
    pipeline still produces exportable clips.
    """
    if not segments:
        return []
    out: list[HighlightCandidate] = []
    cur_start = segments[0].start
    cur_end = segments[0].end
    buf: list[str] = [segments[0].text]

    def flush() -> None:
        nonlocal cur_start, cur_end, buf
        if cur_end > cur_start + 3.0:
            text = " ".join(buf).strip()[:200]
            out.append(
                HighlightCandidate(
                    start=cur_start,
                    end=cur_end,
                    score=0.52,
                    reason=f"Transcript segment (auto): {text or '…'}",
                    source="ai",
                )
            )

    for seg in segments[1:]:
        if seg.start - cur_end > 4.0 or (cur_end - cur_start) >= target_seconds:
            flush()
            cur_start, cur_end = seg.start, seg.end
            buf = [seg.text]
        else:
            cur_end = seg.end
            buf.append(seg.text)
    flush()

    out.sort(key=lambda x: -x.score)
    return out[:max_clips]


def _boost_overlap(ai: HighlightCandidate, signal_clips: list[HighlightCandidate]) -> float:
    """Extra score when an AI window aligns with a signal window (>=1.5s overlap)."""
    for s in signal_clips:
        if overlap_seconds(ai.start, ai.end, s.start, s.end) >= 1.5:
            return 0.12
    return 0.0


def _signal_only_clips(
    ai_clips: list[HighlightCandidate],
    sig_clips: list[HighlightCandidate],
    min_overlap_to_skip: float = 2.5,
) -> list[HighlightCandidate]:
    """Signal segments that are not already well covered by an AI clip."""
    extra: list[HighlightCandidate] = []
    for s in sig_clips:
        covered = 0.0
        for a in ai_clips:
            covered += overlap_seconds(a.start, a.end, s.start, s.end)
        if covered < min_overlap_to_skip:
            extra.append(
                HighlightCandidate(
                    start=s.start,
                    end=s.end,
                    score=min(0.95, s.score * 0.92),
                    reason=f"[signal-only] {s.reason}",
                    source="signal",
                )
            )
    return extra


def run_ai_pipeline(
    wav_path: Path,
    *,
    video_title: str | None,
    max_clips: int,
) -> list[HighlightCandidate]:
    segments = transcribe_wav(wav_path)
    prompt = segments_to_prompt_text(segments)
    llm = analyze_highlights_groq(
        prompt,
        video_title=video_title,
        max_clips=max_clips,
    )
    if llm:
        return llm
    fb = _fallback_highlights_from_transcript(segments, max_clips=max_clips)
    if fb:
        logger.warning("Groq returned 0 clips; using %d transcript-based fallback windows", len(fb))
    return fb


def run_hybrid_pipeline(
    wav_path: Path,
    video_path: Path,
    *,
    video_title: str | None,
    max_clips: int,
) -> list[HighlightCandidate]:
    ai_raw = run_ai_pipeline(wav_path, video_title=video_title, max_clips=max_clips)
    sig_raw = run_signal_detection(wav_path, video_path)

    boosted: list[HighlightCandidate] = []
    for a in ai_raw:
        b = _boost_overlap(a, sig_raw)
        boosted.append(
            HighlightCandidate(
                start=a.start,
                end=a.end,
                score=min(1.0, a.score + b),
                reason=a.reason + (" · cross-validated with signal" if b > 0 else ""),
                source="hybrid" if b > 0 else "ai",
            )
        )

    extras = _signal_only_clips(ai_raw, sig_raw)
    merged = merge_intervals(boosted + extras, max_gap=2.0)
    merged.sort(key=lambda x: -x.score)
    return merged[: max_clips * 2]


def run_detection(
    mode: str,
    wav_path: Path,
    video_path: Path,
    *,
    video_title: str | None,
    max_clips: int,
    min_clip_duration: int,
    score_threshold: float,
    video_duration: float | None,
) -> list[HighlightCandidate]:
    """
    Entry point used by the Celery task.

    ``score_threshold`` is 0.0–1.0 (from API settings).
    """
    mode = (mode or "hybrid").lower().strip()
    logger.info("Detection mode=%s wav=%s video=%s", mode, wav_path, video_path)

    if mode == "ai":
        clips = run_ai_pipeline(wav_path, video_title=video_title, max_clips=max_clips)
    elif mode == "signal":
        clips = run_signal_detection(wav_path, video_path)
    elif mode == "hybrid":
        clips = run_hybrid_pipeline(
            wav_path,
            video_path,
            video_title=video_title,
            max_clips=max_clips,
        )
    else:
        logger.warning("Unknown mode %r — falling back to hybrid", mode)
        clips = run_hybrid_pipeline(
            wav_path,
            video_path,
            video_title=video_title,
            max_clips=max_clips,
        )

    clips = enforce_min_duration(clips, float(min_clip_duration), video_duration)
    thr = float(score_threshold)
    filtered = [c for c in clips if c.score >= thr]
    if not filtered and clips:
        logger.warning(
            "All %d candidates were below score_threshold=%.2f; keeping best %d anyway",
            len(clips),
            thr,
            min(max_clips, len(clips)),
        )
        clips = sorted(clips, key=lambda x: -x.score)[:max_clips]
    else:
        clips = filtered
        clips.sort(key=lambda x: -x.score)
        clips = clips[:max_clips]

    logger.info("Detection produced %d clips after threshold & cap", len(clips))
    return clips
