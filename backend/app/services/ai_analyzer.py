import re
import json
import httpx
from app.core.config import get_settings

settings = get_settings()

# Max transcript length to send to AI (prevent huge context + prompt injection)
MAX_TRANSCRIPT_CHARS = 8000

PROMPT_TEMPLATE = """You are a social media content editor. Analyze this YouTube video transcript and identify the BEST moments for a short viral clip (30-60 seconds).

TRANSCRIPT:
{transcript}

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
    Send transcript to Ollama (OpenAI-compatible API), get key moments + metadata.
    Returns dict with: moments, title, description, tags
    """
    safe_transcript = _sanitize_transcript(transcript)
    prompt = PROMPT_TEMPLATE.format(transcript=safe_transcript)

    payload = {
        "model": settings.ollama_model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
        "max_tokens": 1000,
        "stream": False,
    }

    base_url = settings.ollama_base_url.rstrip("/")

    try:
        resp = httpx.post(
            f"{base_url}/v1/chat/completions",
            json=payload,
            timeout=120,
        )
        resp.raise_for_status()
        data = resp.json()
        raw = data["choices"][0]["message"]["content"].strip()
    except httpx.HTTPStatusError as e:
        detail = e.response.text[:300]
        raise RuntimeError(f"Ollama request failed ({e.response.status_code}): {detail}")
    except Exception as e:
        raise RuntimeError(f"Ollama request failed: {e}")

    # Strip markdown fences if the model added them despite instructions
    raw = re.sub(r"^```json\s*", "", raw)
    raw = re.sub(r"^```\w*\s*", "", raw)
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
