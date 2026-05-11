"""Shared types and interval helpers for Phase 2 detection."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class TranscriptSegment:
    start: float
    end: float
    text: str


@dataclass
class HighlightCandidate:
    start: float
    end: float
    score: float  # 0.0 – 1.0
    reason: str
    source: str  # "ai" | "signal" | "hybrid"


def overlap_seconds(a_start: float, a_end: float, b_start: float, b_end: float) -> float:
    lo = max(a_start, b_start)
    hi = min(a_end, b_end)
    return max(0.0, hi - lo)


def merge_intervals(
    items: list[HighlightCandidate],
    max_gap: float = 2.0,
) -> list[HighlightCandidate]:
    """Merge candidates that overlap or are within ``max_gap`` seconds."""
    if not items:
        return []
    sorted_items = sorted(items, key=lambda x: (x.start, x.end))
    out: list[HighlightCandidate] = []
    cur = sorted_items[0]
    for nxt in sorted_items[1:]:
        if nxt.start <= cur.end + max_gap:
            cur = HighlightCandidate(
                start=cur.start,
                end=max(cur.end, nxt.end),
                score=max(cur.score, nxt.score),
                reason=cur.reason if cur.score >= nxt.score else nxt.reason,
                source=cur.source if cur.source == nxt.source else "both",
            )
        else:
            out.append(cur)
            cur = nxt
    out.append(cur)
    return out


def enforce_min_duration(
    clips: list[HighlightCandidate],
    min_dur: float,
    video_duration: float | None,
) -> list[HighlightCandidate]:
    """Extend clip end to ``min_dur`` where possible without exceeding video length."""
    fixed: list[HighlightCandidate] = []
    vmax = video_duration if video_duration and video_duration > 0 else float("inf")
    for c in clips:
        dur = c.end - c.start
        if dur >= min_dur:
            fixed.append(c)
            continue
        need = min_dur - dur
        new_end = min(c.end + need, vmax)
        new_start = max(0.0, c.start - max(0, need - (new_end - c.end)))
        fixed.append(
            HighlightCandidate(
                start=new_start,
                end=max(new_end, new_start + min_dur * 0.99),
                score=c.score,
                reason=c.reason,
                source=c.source,
            )
        )
    return fixed
