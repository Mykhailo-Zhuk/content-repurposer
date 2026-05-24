import re
import json
from app.core.config import get_settings

settings = get_settings()

# Max transcript length to send to AI (prevent huge context + prompt injection)
MAX_TRANSCRIPT_CHARS = 8000


def _sanitize_transcript(transcript: str) -> str:
    """
    Sanitize transcript before sending to AI to prevent prompt injection.
    - Truncate to max length
    - Remove suspicious instruction-like patterns
    """
    # Truncate
    transcript = transcript[:MAX_TRANSCRIPT_CHARS]

    # Remove common prompt injection attempts
    injection_patterns = [
        r"ignore (all |previous |above )?instructions?",
        r"you are now",
        r"new instructions?:",
        r"system prompt",
        r"forget everything",
    ]
    for pattern in injection_patterns:
        transcript = re.sub(pattern, "[REMOVED]", transcript, flags=re.IGNORECASE)

    return transcript


def analyze_transcript(transcript: str) -> dict:
    """
    Send transcript to Gemini, get key moments + metadata for short video.
    Returns dict with: moments, title, description, tags
    """
    if not settings.gemini_api_key:
        raise RuntimeError("GEMINI_API_KEY not configured")

    import google.generativeai as genai

    genai.configure(api_key=settings.gemini_api_key)
    model = genai.GenerativeModel("gemini-1.5-flash")

    safe_transcript = _sanitize_transcript(transcript)

    prompt = f"""You are a social media content editor. Analyze this YouTube video transcript and identify the BEST moments for a short viral clip (30-60 seconds).

TRANSCRIPT:
{safe_transcript}

Respond ONLY with valid JSON (no markdown, no explanation):
{{
  "moments": [
    {{
      "start_text": "exact phrase where clip should start",
      "end_text": "exact phrase where clip should end",
      "reason": "why this moment is engaging"
    }}
  ],
  "title": "catchy title for the short (max 60 chars)",
  "description": "engaging description for social media (max 150 chars)",
  "tags": ["tag1", "tag2", "tag3", "tag4", "tag5"]
}}

Pick the single most engaging moment. Focus on: surprising facts, emotional peaks, clear value, or humor."""

    response = model.generate_content(prompt)
    raw = response.text.strip()

    # Strip markdown fences if model added them despite instructions
    raw = re.sub(r"^```json\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)

    try:
        result = json.loads(raw)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"AI returned invalid JSON: {e}")

    # Validate required fields
    required = {"moments", "title", "description", "tags"}
    if not required.issubset(result.keys()):
        raise RuntimeError(f"AI response missing fields: {required - result.keys()}")

    return result
