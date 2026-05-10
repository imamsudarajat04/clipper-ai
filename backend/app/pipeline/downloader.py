"""
yt-dlp wrapper — downloads a YouTube video to disk.
Emits progress via a callback so the Celery task can update job state.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Callable

import yt_dlp


class DownloadError(Exception):
    pass


def _sanitize_filename(name: str, max_len: int = 80) -> str:
    """Remove filesystem-unsafe characters and truncate."""
    name = re.sub(r'[\\/:*?"<>|]', "_", name)
    return name[:max_len].strip()


def download_video(
    url: str,
    output_dir: Path,
    progress_cb: Callable[[int, str], None] | None = None,
) -> dict:
    """
    Download a YouTube video.

    Args:
        url: YouTube URL
        output_dir: Directory to save the video
        progress_cb: Optional callback(percent: int, message: str)

    Returns:
        dict with keys: path, title, duration, thumbnail_url
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    result: dict = {}

    def _hook(d: dict) -> None:
        if d["status"] == "downloading":
            raw = d.get("_percent_str", "0%").strip().replace("%", "")
            try:
                pct = int(float(raw))
            except ValueError:
                pct = 0
            speed = d.get("_speed_str", "")
            eta = d.get("_eta_str", "")
            msg = f"Downloading… {pct}% | {speed} | ETA {eta}"
            if progress_cb:
                progress_cb(pct, msg)
        elif d["status"] == "finished":
            result["path"] = Path(d["filename"])
            if progress_cb:
                progress_cb(100, "Download complete")

    ydl_opts = {
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "outtmpl": str(output_dir / "%(id)s.%(ext)s"),
        "merge_output_format": "mp4",
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "progress_hooks": [_hook],
        "postprocessors": [],
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if info is None:
                raise DownloadError("yt-dlp returned no info")

            video_id = info.get("id", "unknown")
            title = info.get("title", "Untitled")
            duration = info.get("duration", 0)
            thumbnail = info.get("thumbnail", None)

            # Resolve final path (may differ by extension)
            if "path" not in result:
                for ext in ["mp4", "mkv", "webm"]:
                    candidate = output_dir / f"{video_id}.{ext}"
                    if candidate.exists():
                        result["path"] = candidate
                        break

            if "path" not in result:
                raise DownloadError(f"Downloaded file not found for video id={video_id}")

            result.update(
                {
                    "title": title,
                    "video_id": video_id,
                    "duration": duration,
                    "thumbnail_url": thumbnail,
                }
            )
            return result

    except yt_dlp.utils.DownloadError as exc:
        raise DownloadError(str(exc)) from exc
