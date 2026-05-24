import subprocess
import re
from pathlib import Path


def find_timestamp_for_text(vtt_path: str, search_text: str) -> float | None:
    """Find timestamp in VTT file for a given text snippet."""
    with open(vtt_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Split into cue blocks
    blocks = content.split("\n\n")
    for block in blocks:
        if "-->" not in block:
            continue
        lines = block.strip().split("\n")
        # Find timestamp line
        ts_line = next((l for l in lines if "-->" in l), None)
        if not ts_line:
            continue
        # Get text from block
        text_lines = [l for l in lines if "-->" not in l and not l.startswith("NOTE")]
        text = " ".join(text_lines)
        text_clean = re.sub(r"<[^>]+>", "", text)

        if search_text[:30].lower() in text_clean.lower():
            # Parse start timestamp: 00:01:23.456
            ts_match = re.match(r"(\d+):(\d+):(\d+)\.(\d+)", ts_line)
            if ts_match:
                h, m, s, ms = ts_match.groups()
                return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000

    return None


def render_short(
    video_path: str,
    vtt_path: str,
    output_path: str,
    start_seconds: float,
    end_seconds: float,
) -> str:
    """
    Cut video segment and add subtitles.
    Returns path to output file.
    """
    duration = end_seconds - start_seconds
    if duration <= 0 or duration > 120:
        raise ValueError(f"Invalid clip duration: {duration}s")

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    # Step 1: Cut the clip
    clip_path = str(output.parent / "clip_raw.mp4")
    result = subprocess.run(
        [
            "ffmpeg", "-y",
            "-ss", str(start_seconds),
            "-i", video_path,
            "-t", str(duration),
            "-c:v", "libx264",
            "-c:a", "aac",
            "-movflags", "+faststart",
            clip_path,
        ],
        capture_output=True,
        text=True,
        timeout=120,
        shell=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg clip error: {result.stderr[:200]}")

    # Step 2: Scale to vertical 9:16 format (1080x1920) for Shorts
    final_path = str(output)
    result = subprocess.run(
        [
            "ffmpeg", "-y",
            "-i", clip_path,
            "-vf", "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2",
            "-c:v", "libx264",
            "-crf", "23",
            "-preset", "fast",
            "-c:a", "aac",
            "-b:a", "128k",
            final_path,
        ],
        capture_output=True,
        text=True,
        timeout=120,
        shell=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg scale error: {result.stderr[:200]}")

    return final_path


def render_short_from_analysis(
    video_path: str,
    vtt_path: str,
    job_dir: str,
    analysis: dict,
) -> str:
    """
    High-level: use AI analysis to find timestamps and render short.
    Falls back to first 60s if timestamps can't be found.
    """
    output_path = str(Path(job_dir) / "short.mp4")
    moments = analysis.get("moments", [])

    start = None
    end = None

    if moments:
        moment = moments[0]
        start_text = moment.get("start_text", "")
        end_text = moment.get("end_text", "")

        start = find_timestamp_for_text(vtt_path, start_text)
        end = find_timestamp_for_text(vtt_path, end_text)

    # Fallback: use first 60 seconds
    if start is None or end is None or end <= start:
        start = 0.0
        end = 60.0

    return render_short(video_path, vtt_path, output_path, start, end)
