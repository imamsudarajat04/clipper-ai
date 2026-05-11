"""
Groq LLM — highlight timestamps from transcript.
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any

from groq import Groq

from app.core.config import settings
from app.pipeline.detect_types import HighlightCandidate

logger = logging.getLogger(__name__)


class GroqHighlightError(Exception):
    pass


def _extract_json_array(text: str) -> list[dict[str, Any]]:
    """Parse first JSON array from model output (handles markdown fences)."""
    cleaned = text.strip()
    if "```" in cleaned:
        m = re.search(r"```(?:json)?\s*(\[.*?\])\s*```", cleaned, re.DOTALL | re.IGNORECASE)
        if m:
            cleaned = m.group(1)
    m2 = re.search(r"\[.*\]", cleaned, re.DOTALL)
    if not m2:
        raise ValueError("No JSON array found in model response")
    return json.loads(m2.group(0))


def analyze_highlights_groq(
    transcript_with_timestamps: str,
    *,
    video_title: str | None,
    max_clips: int,
    model: str | None = None,
) -> list[HighlightCandidate]:
    """
    Ask Groq to propose highlight windows with scores 0–100 (mapped to 0–1).
    """
    key = (settings.GROQ_API_KEY or "").strip()
    if not key:
        raise GroqHighlightError("GROQ_API_KEY is not set — required for AI detection mode.")

    client = Groq(api_key=key)
    model_id = (model or settings.GROQ_MODEL or "llama-3.3-70b-versatile").strip()

    title_ctx = (f"Title: {video_title}\n" if video_title else "")
    prompt = f"""{title_ctx}You are a YouTube editor. Transcript lines are [start–end] text.
Pick up to {max_clips} highlight moments (4–90s each). Return ONLY a JSON array:
[{{"start": float, "end": float, "reason": "short", "score": 0-100}}]
Use timestamps from the transcript. Prefer strong moments.

Transcript:
{transcript_with_timestamps}
"""

    logger.info(
        "Groq request model=%s max_clips=%d transcript_chars=%d",
        model_id,
        max_clips,
        len(transcript_with_timestamps),
    )

    def _call(user_content: str):
        return client.chat.completions.create(
            model=model_id,
            messages=[
                {
                    "role": "system",
                    "content": "Reply with only a JSON array, no markdown.",
                },
                {"role": "user", "content": user_content},
            ],
            temperature=0.25,
            max_tokens=2048,
        )

    try:
        chat = _call(prompt)
    except Exception as exc:
        err = str(exc)
        if ("413" in err or "rate_limit" in err.lower() or "tokens per minute" in err.lower()) and len(
            transcript_with_timestamps
        ) > 800:
            logger.warning("Groq TPM/rate hit — retrying with shorter transcript slice")
            tlen = len(transcript_with_timestamps)
            # 8b-instant ~6K TPM total; keep retry body small (chars ≈ lower bound on tokens).
            short_len = min(1600, max(400, tlen // 5))
            short = transcript_with_timestamps[:short_len]
            prompt2 = prompt.replace(transcript_with_timestamps, short + "\n… [transcript shortened for TPM]")
            try:
                chat = _call(prompt2)
            except Exception as exc2:
                logger.exception("Groq retry failed")
                raise GroqHighlightError(f"Groq API error: {exc2}") from exc2
        else:
            logger.exception("Groq API request failed")
            raise GroqHighlightError(f"Groq API error: {exc}") from exc

    text = (chat.choices[0].message.content or "").strip()
    if not text:
        raise GroqHighlightError("Groq returned empty content")

    try:
        raw_list = _extract_json_array(text)
    except (json.JSONDecodeError, ValueError) as exc:
        logger.error("Groq JSON parse failed. Raw (truncated): %s", text[:800])
        raise GroqHighlightError(f"Could not parse Groq JSON: {exc}") from exc

    out: list[HighlightCandidate] = []
    for i, item in enumerate(raw_list):
        if not isinstance(item, dict):
            continue
        try:
            start = float(item["start"])
            end = float(item["end"])
            reason = str(item.get("reason", "LLM highlight")).strip() or "LLM highlight"
            score_raw = float(item.get("score", 70))
            score = max(0.0, min(100.0, score_raw)) / 100.0
        except (KeyError, TypeError, ValueError) as exc:
            logger.warning("Skipping invalid Groq item %s: %s", item, exc)
            continue
        if end <= start:
            continue
        out.append(
            HighlightCandidate(
                start=start,
                end=end,
                score=score,
                reason=reason,
                source="ai",
            )
        )

    out.sort(key=lambda x: -x.score)
    logger.info("Groq returned %d highlight candidates", len(out))
    return out[: max_clips * 2]
