"""
Signal-based highlight detection: PyDub RMS energy + OpenCV scene cuts.
"""
from __future__ import annotations

import logging
from pathlib import Path

import cv2
import numpy as np
from pydub import AudioSegment

from app.core.config import settings
from app.pipeline.detect_types import HighlightCandidate, merge_intervals, overlap_seconds as _overlap

logger = logging.getLogger(__name__)


def _rms_windows(wav_path: Path, window_ms: int) -> tuple[list[float], list[tuple[float, float]]]:
    """Return per-window RMS (linear) and (start_s, end_s) for each window."""
    seg = AudioSegment.from_file(str(wav_path), format="wav")
    duration_ms = len(seg)
    window_ms = max(200, window_ms)
    rms_vals: list[float] = []
    spans: list[tuple[float, float]] = []
    pos = 0
    while pos < duration_ms:
        chunk = seg[pos : pos + window_ms]
        pos += window_ms
        # pydub RMS in dBFS can be -inf for silence; convert to linear power proxy
        db = chunk.dBFS
        if db == float("-inf"):
            rms_lin = 0.0
        else:
            rms_lin = float(np.exp(np.clip(db / 20.0 * np.log(10), -50, 50)))
        rms_vals.append(rms_lin)
        t0 = (pos - window_ms) / 1000.0
        t1 = min(pos, duration_ms) / 1000.0
        spans.append((t0, t1))
    return rms_vals, spans


def _energy_highlights(wav_path: Path) -> list[HighlightCandidate]:
    window_ms = settings.SIGNAL_WINDOW_MS
    pct = float(np.clip(settings.SIGNAL_RMS_PERCENTILE, 0.5, 0.99))
    rms, spans = _rms_windows(wav_path, window_ms)
    if not rms:
        return []
    arr = np.array(rms, dtype=np.float64)
    thresh = float(np.quantile(arr, pct))
    if thresh <= 1e-9:
        thresh = float(np.max(arr)) * 0.5

    raw: list[HighlightCandidate] = []
    for val, (t0, t1) in zip(rms, spans):
        if val >= thresh:
            score = float(min(1.0, 0.55 + 0.45 * (val / (thresh + 1e-9) - 1.0)))
            raw.append(
                HighlightCandidate(
                    start=t0,
                    end=t1,
                    score=score,
                    reason="High RMS audio energy",
                    source="signal",
                )
            )
    merged = merge_intervals(raw, max_gap=2.0)
    logger.info("Energy detection: %d windows above threshold → %d merged segments", len(raw), len(merged))
    return merged


def _scene_highlights(video_path: Path) -> list[HighlightCandidate]:
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        logger.warning("OpenCV could not open video: %s", video_path)
        return []

    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    if frame_count <= 0:
        cap.release()
        return []

    # Sample ~2 fps for speed
    step = max(1, int(round(fps / 2.0)))
    thresh = settings.SCENE_DIFF_THRESHOLD
    min_gap_frames = int(settings.SCENE_MIN_INTERVAL_S * fps)

    prev_small: np.ndarray | None = None
    last_trigger = -min_gap_frames
    events: list[float] = []

    idx = 0
    while idx < frame_count:
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ok, frame = cap.read()
        if not ok or frame is None:
            break
        small = cv2.resize(frame, (160, 90), interpolation=cv2.INTER_AREA)
        gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
        if prev_small is not None:
            diff = cv2.absdiff(gray, prev_small)
            mean_diff = float(np.mean(diff))
            if mean_diff >= thresh and (idx - last_trigger) >= min_gap_frames:
                t = idx / fps
                events.append(t)
                last_trigger = idx
        prev_small = gray
        idx += step

    cap.release()

    out: list[HighlightCandidate] = []
    for t in events:
        out.append(
            HighlightCandidate(
                start=max(0.0, t - 0.5),
                end=t + 2.0,
                score=0.62,
                reason="Scene change (frame difference)",
                source="signal",
            )
        )
    merged = merge_intervals(out, max_gap=2.0)
    logger.info("Scene detection: %d cuts → %d merged segments", len(events), len(merged))
    return merged


def run_signal_detection(wav_path: Path, video_path: Path) -> list[HighlightCandidate]:
    """Combine audio-energy and scene-based candidates, merge overlaps (<2s gap)."""
    audio_h = _energy_highlights(wav_path)
    scene_h = _scene_highlights(video_path)
    combined = audio_h + scene_h
    merged = merge_intervals(combined, max_gap=2.0)
    refined: list[HighlightCandidate] = []
    for c in merged:
        has_a = any(_overlap(c.start, c.end, a.start, a.end) > 0.3 for a in audio_h)
        has_s = any(_overlap(c.start, c.end, s.start, s.end) > 0.3 for s in scene_h)
        if has_a and has_s:
            subtype = "both"
        elif has_s:
            subtype = "scene"
        else:
            subtype = "audio"
        boost = 0.1 if has_a and has_s else 0.0
        reason = f"[{subtype}] {c.reason}"
        refined.append(
            HighlightCandidate(
                start=c.start,
                end=c.end,
                score=min(1.0, c.score + boost),
                reason=reason,
                source="signal",
            )
        )
    return refined
