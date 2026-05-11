"""
yt-dlp wrapper — downloads a YouTube video to disk.
Emits progress via a callback so the Celery task can update job state.
"""
from __future__ import annotations

import logging
import os
import re
import tempfile
from pathlib import Path
from typing import Callable

import yt_dlp

from app.core.config import settings

logger = logging.getLogger(__name__)


class DownloadError(Exception):
    pass


def _writable_cookie_copy(src: Path) -> str:
    """
    yt-dlp updates the cookie jar on disk. The bind-mounted host file is often not
    writable by user ``clipper``. Some hosts also block reads from the mount for
    non-owners until permissions are fixed.

    Strategy: read bytes from ``src`` (clear error if EACCES), write a fresh file
    under ``/tmp`` (always writable), pass that path to yt-dlp.
    """
    try:
        raw = src.read_bytes()
    except OSError as exc:
        raise DownloadError(
            f"Cannot read cookies file {src}: {exc}. "
            "On the host, from the project root: chmod a+r data/cookies.txt "
            "(or chown the file to the UID used inside the container). "
            "SELinux: try volume flag :z on ./data mount."
        ) from exc

    fd, name = tempfile.mkstemp(prefix="clipper_ytdlp_", suffix="_cookies.txt", dir="/tmp")
    try:
        os.write(fd, raw)
    except OSError as exc:
        os.close(fd)
        try:
            os.unlink(name)
        except OSError:
            pass
        raise DownloadError(f"Cannot write cookie temp file under /tmp: {exc}") from exc
    os.close(fd)

    path = Path(name)
    try:
        path.chmod(0o600)
    except OSError:
        pass
    logger.info(
        "yt-dlp cookies: temp jar %s (%d bytes) from %s",
        path,
        len(raw),
        src,
    )
    return str(path)


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
            # Do not set result["path"] here — for bestvideo+bestaudio, "finished" fires per
            # fragment (.f140.m4a etc.); those files are removed after merge into .mp4.
            if progress_cb:
                progress_cb(100, "Download complete")

    ydl_opts: dict = {
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "outtmpl": str(output_dir / "%(id)s.%(ext)s"),
        "merge_output_format": "mp4",
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "progress_hooks": [_hook],
        "postprocessors": [],
    }

    cookies_path = (settings.YTDLP_COOKIES_FILE or "").strip()
    cookie_temp: str | None = None
    if cookies_path:
        cfile = Path(cookies_path)
        if cfile.is_file():
            cookie_temp = _writable_cookie_copy(cfile)
            ydl_opts["cookiefile"] = cookie_temp
        else:
            logger.warning(
                "YTDLP_COOKIES_FILE is set but file is missing or not readable: %s "
                "(YouTube bot challenges need a valid Netscape cookies.txt inside the worker container)",
                cfile,
            )

    # yt-dlp / deps may also read this env and try to open the bind-mounted path for writes.
    env_cookies_backup: str | None = None
    if cookie_temp is not None and "YTDLP_COOKIES_FILE" in os.environ:
        env_cookies_backup = os.environ.pop("YTDLP_COOKIES_FILE")

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if info is None:
                raise DownloadError("yt-dlp returned no info")

            video_id = info.get("id", "unknown")
            title = info.get("title", "Untitled")
            duration = info.get("duration", 0)
            thumbnail = info.get("thumbnail", None)

            # Resolve merged output path (never use merge-fragment paths like *.f140.m4a)
            candidates: list[Path] = []
            fp = info.get("filepath")
            if fp:
                candidates.append(Path(fp))
            try:
                candidates.append(Path(ydl.prepare_filename(info)))
            except (OSError, ValueError, KeyError):
                pass
            for ext in ("mp4", "mkv", "webm"):
                candidates.append(output_dir / f"{video_id}.{ext}")

            resolved: Path | None = None
            for p in candidates:
                try:
                    if p.is_file():
                        resolved = p.resolve()
                        break
                except OSError:
                    continue

            if resolved is None:
                raise DownloadError(
                    f"Downloaded file not found for video id={video_id} "
                    f"(checked merged path and {video_id}.mp4/mkv/webm)"
                )
            result["path"] = resolved

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
        msg = str(exc)
        if "Sign in to confirm" in msg or "not a bot" in msg:
            hint = (
                " YouTube is blocking this client. Export a Netscape cookies.txt while logged in, "
                "set YTDLP_COOKIES_FILE to its path (e.g. /data/youtube_cookies.txt in Docker), "
                "and restart the worker. See https://github.com/yt-dlp/yt-dlp/wiki/Extractors#exporting-youtube-cookies"
            )
            if not cookies_path or not Path(cookies_path).is_file():
                msg += hint
            else:
                msg += (
                    " (YTDLP_COOKIES_FILE is set but download still failed — refresh cookies or check path/read access.)"
                )
        raise DownloadError(msg) from exc
    finally:
        if env_cookies_backup is not None:
            os.environ["YTDLP_COOKIES_FILE"] = env_cookies_backup
        if cookie_temp:
            try:
                Path(cookie_temp).unlink(missing_ok=True)
            except OSError:
                logger.debug("Could not remove temp cookie file %s", cookie_temp, exc_info=True)
