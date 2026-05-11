"""
Cut highlight clips from source video using ffmpeg (libx264 + aac or VP9 + Opus).
"""
from __future__ import annotations

import logging
import subprocess
from pathlib import Path
from typing import TypedDict


logger = logging.getLogger(__name__)


class ClipExportError(Exception):
    pass


class _FmtCfg(TypedDict):
    vcodec: str
    acodec: str
    ext: str
    extra: list[str]


_FMT: dict[str, _FmtCfg] = {
    "webm": {
        "vcodec": "libvpx-vp9",
        "acodec": "libopus",
        "ext": ".webm",
        "extra": ["-crf", "35", "-b:v", "0"],
    },
    "mp4": {
        "vcodec": "libx264",
        "acodec": "aac",
        "ext": ".mp4",
        "extra": ["-preset", "veryfast", "-crf", "23", "-movflags", "+faststart"],
    },
}


def export_clip(
    video_src: Path,
    start: float,
    end: float,
    out_path: Path,
    *,
    output_format: str = "mp4",
) -> Path:
    """
    Extract [start, end] from ``video_src`` into ``out_path``.

    Re-encodes for robust seek (copy mode can fail on some DASH merges).
    """
    duration = max(0.1, end - start)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fmt = (output_format or "mp4").lower().strip()
    if fmt not in _FMT:
        fmt = "mp4"
    cfg = _FMT[fmt]

    ext = cfg["ext"]
    if out_path.suffix.lower() != ext:
        out_path = out_path.with_suffix(ext)

    cmd: list[str] = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-ss",
        f"{start:.3f}",
        "-i",
        str(video_src),
        "-t",
        f"{duration:.3f}",
        "-c:v",
        cfg["vcodec"],
        "-c:a",
        cfg["acodec"],
        *cfg["extra"],
        str(out_path),
    ]

    logger.info("ffmpeg clip: %s -> %s", video_src.name, out_path.name)
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as exc:
        err = (exc.stderr or "") + (exc.stdout or "")
        logger.error("ffmpeg clip failed: %s", err[-2000:])
        raise ClipExportError(f"ffmpeg clip export failed: {err[-800:]}") from exc

    if not out_path.is_file():
        raise ClipExportError(f"Clip file not created: {out_path}")

    return out_path
