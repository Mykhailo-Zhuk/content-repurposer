---
tags: [ope-167, gemini, ai, transcript, analysis, prompt]
created: 2026-05-17
status: active
relates-to: "[[00 — OPE-167 Огляд проекту]]"
---

# 04 — Gemini AI аналіз

## Призначення

Gemini отримує текст transcript YouTube відео і повертає:
- Найкращий момент для нарізки (початок і кінець у вигляді текстових фрагментів)
- Заголовок (title) для short
- Опис (description) для соцмереж
- Хештеги (tags)

Файл: `backend/app/services/ai_analyzer.py`

## Модель та параметри

| Параметр | Значення |
|---|---|
| Модель | `gemini-1.5-flash` |
| Бібліотека | `google-generativeai` |
| max_tokens | 1000 |
| Формат відповіді | JSON (без markdown) |

`gemini-1.5-flash` обрана за швидкість і вартість — для MVP достатньо. При необхідності більшої точності можна переключити на `gemini-1.5-pro`.

## Аутентифікація

```python
import google.generativeai as genai
genai.configure(api_key=settings.gemini_api_key)
model = genai.GenerativeModel("gemini-1.5-flash")
```

API ключ — виключно з `GEMINI_API_KEY` в `.env`. Ніколи в коді.

## Промпт

```
You are a social media content editor. Analyze this YouTube video transcript
and identify the BEST moments for a short viral clip (30-60 seconds).

TRANSCRIPT:
{sanitized_transcript}

Respond ONLY with valid JSON (no markdown, no explanation):
{
  "moments": [
    {
      "start_text": "exact phrase where clip should start",
      "end_text": "exact phrase where clip should end",
      "reason": "why this moment is engaging"
    }
  ],
  "title": "catchy title for the short (max 60 chars)",
  "description": "engaging description for social media (max 150 chars)",
  "tags": ["tag1", "tag2", "tag3", "tag4", "tag5"]
}

Pick the single most engaging moment.
Focus on: surprising facts, emotional peaks, clear value, or humor.
```

## Формат відповіді

```json
{
  "moments": [
    {
      "start_text": "And the most surprising thing about this is",
      "end_text": "which is why this changes everything",
      "reason": "Emotional peak with clear value proposition"
    }
  ],
  "title": "Why This Changes Everything 🔥",
  "description": "The surprising truth nobody talks about. Save this before it's gone.",
  "tags": ["shorts", "viral", "mindblowing", "explained", "mustsee"]
}
```

## Санітизація транскрипту

Перед передачею в Gemini транскрипт проходить санітизацію (`_sanitize_transcript`):

**1. Обрізка до MAX_TRANSCRIPT_CHARS (8000 символів)**
Запобігає надмірним витратам токенів і timeout.

**2. Видалення prompt injection патернів:**
```python
injection_patterns = [
    r"ignore (all |previous |above )?instructions?",
    r"you are now",
    r"new instructions?:",
    r"system prompt",
    r"forget everything",
]
```

Замінюються на `[REMOVED]`. Захищає від випадку, коли відео навмисно містить маніпуляції для AI.

## Парсинг відповіді

```python
response = model.generate_content(prompt)
raw = response.text.strip()

# Видалення markdown fences (якщо модель проігнорувала інструкцію)
raw = re.sub(r"^```json\s*", "", raw)
raw = re.sub(r"\s*```$", "", raw)

result = json.loads(raw)

# Валідація обов'язкових полів
required = {"moments", "title", "description", "tags"}
if not required.issubset(result.keys()):
    raise RuntimeError(f"AI response missing fields: ...")
```

## Крайні випадки

| Ситуація | Поведінка |
|---|---|
| `GEMINI_API_KEY` не встановлено | `RuntimeError("GEMINI_API_KEY not configured")` |
| Модель повернула не-JSON | `RuntimeError("AI returned invalid JSON")` |
| Відсутні обов'язкові поля | `RuntimeError("AI response missing fields")` |
| API timeout / 503 | Celery retry (max 2 рази) |
| Quota exceeded (429) | Celery retry з `default_retry_delay=10` |
| Transcript порожній | Gemini поверне порожні моменти → fallback 0–60 сек у renderer |

## Отримання Gemini API Key

1. Відкрити https://aistudio.google.com/app/apikey
2. Натиснути **Create API key**
3. Скопіювати ключ у `.env`:
   ```
   GEMINI_API_KEY=AIzaSy...
   ```

> **Безкоштовний tier:** 15 запитів/хв, 1500 запитів/день — достатньо для MVP.

## Порівняння з OPE-10

OPE-10 використовує Ollama Cloud API (ministral-3:8b) для генерації YouTube Description. OPE-167 використовує Gemini — більш потужна модель, краще розуміє англомовний контент, оптимальніша для аналізу transcript.

| | OPE-10 | OPE-167 |
|---|---|---|
| AI провайдер | Ollama Cloud | Google Gemini |
| Модель | ministral-3:8b | gemini-1.5-flash |
| Задача | Генерація опису за шаблоном | Аналіз + вибір моменту |
| Temperature | 0.4 | default |
| Мова виводу | Українська | Англійська (для глобального охоплення) |

## Пов'язані нотатки

- [[03 — Pipeline обробки відео]]
- [[05 — Безпека]]
- [[00 — OPE-10 Огляд проекту]] — Ollama Cloud API (аналогічна AI інтеграція)
