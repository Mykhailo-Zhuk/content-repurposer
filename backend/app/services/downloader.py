import subprocess
import os
import re
from pathlib import Path
from app.core.config import get_settings

settings = get_settings()

MAX_DURATION_SECONDS = 30 * 60  # 30 min

YOUTUBE_URL_RE = re.compile(
    r"^https://(www\.)?(youtube\.com/watch\?v=[\w-]{11}|youtu\.be/[\w-]{11})"
)


def _safe_url(url: str) -> str:
    """Validate URL again before passing to yt-dlp (defense in depth)."""
    if not YOUTUBE_URL_RE.match(url):
        raise ValueError("Invalid YouTube URL")
    return url


def get_video_info(url: str) -> dict:
    """Fetch video metadata without downloading."""
    safe_url = _safe_url(url)
    result = subprocess.run(
        [
            "yt-dlp",
            "--dump-json",
            "--no-playlist",
            safe_url,
        ],
        capture_output=True,
        text=True,
        timeout=30,
        shell=False,  # ВАЖЛИВО: shell=False
    )
    if result.returncode != 0:
        raise RuntimeError(f"yt-dlp error: {result.stderr[:200]}")

    import json
    info = json.loads(result.stdout)

    duration = info.get("duration", 0)
    if duration > MAX_DURATION_SECONDS:
        raise ValueError(f"Відео занадто довге: {duration // 60} хв (ліміт 30 хв)")

    return {
        "title": info.get("title", ""),
        "duration": duration,
        "video_id": info.get("id", ""),
    }


def download_video_and_transcript(url: str, job_dir: Path) -> dict:
    """
    Download video + auto-subtitles into job_dir.
    Returns paths to downloaded files.
    """
    safe_url = _safe_url(url)
    job_dir.mkdir(parents=True, exist_ok=True)

    video_path = job_dir / "video.mp4"
    subtitle_path = job_dir / "video.en.vtt"

    # Download video (max 2GB via --max-filesize)
    result = subprocess.run(
        [
            "yt-dlp",
            "--no-playlist",
            "--max-filesize", "2G",
            "--format", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]",
            "--write-auto-sub",
            "--sub-lang", "en",
            "--sub-format", "vtt",
            "--output", str(video_path),
            safe_url,
        ],
        capture_output=True,
        text=True,
        timeout=300,  # 5 min max
        shell=False,
    )

    if result.returncode != 0:
        stderr = result.stderr[:300]
        if "Private video" in stderr:
            raise ValueError("Відео приватне або недоступне")
        if "No video formats" in stderr:
            raise ValueError("Не вдалось знайти формат відео")
        raise RuntimeError(f"Download failed: {stderr}")

    # Check subtitle file exists (yt-dlp may name it differently)
    vtt_files = list(job_dir.glob("*.vtt"))
    if not vtt_files:
        raise ValueError("Субтитри не знайдено. Спробуйте відео з автоматичними субтитрами")

    return {
        "video_path": str(video_path),
        "subtitle_path": str(vtt_files[0]),
    }


def parse_vtt(vtt_path: str) -> str:
    """Extract plain text from VTT subtitle file."""
    text_lines = []
    with open(vtt_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            # Skip WEBVTT header, timestamps, and empty lines
            if (
                not line
                or line.startswith("WEBVTT")
                or line.startswith("NOTE")
                or "-->" in line
                or line.isdigit()
            ):
                continue
            # Strip HTML tags from subtitles
            clean = re.sub(r"<[^>]+>", "", line)
            if clean:
                text_lines.append(clean)

    # Deduplicate consecutive identical lines
    deduped = []
    for line in text_lines:
        if not deduped or deduped[-1] != line:
            deduped.append(line)

    return " ".join(deduped)
