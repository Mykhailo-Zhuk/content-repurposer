---
tags: [ope-167, pipeline, celery, yt-dlp, ffmpeg, video]
created: 2026-05-17
status: active
relates-to: "[[00 — OPE-167 Огляд проекту]]"
---

# 03 — Pipeline обробки відео

## Загальна схема

```
process_video (Celery task)
        │
        ▼ [10%] DOWNLOADING
   download_video_and_transcript(url, job_dir)
        │
        ├── yt-dlp → video.mp4
        └── yt-dlp --write-auto-sub → video.en.vtt
        │
        ▼ [40%] ANALYZING
   parse_vtt(subtitle_path)
        │
        └── plain text transcript
        │
        ▼ [60%] ANALYZING
   analyze_transcript(transcript)  [Gemini]
        │
        └── { moments, title, description, tags }
        │
        ▼ [75%] RENDERING
   render_short_from_analysis(video, vtt, job_dir, analysis)
        │
        ├── find_timestamp_for_text() → start/end seconds
        ├── ffmpeg cut → clip_raw.mp4
        └── ffmpeg scale → short.mp4 (1080×1920)
        │
        ▼ [100%] DONE
   update_job(DONE, result={video_url, title, description, tags})
```

## Celery Task

```python
@celery_app.task(bind=True, max_retries=2, default_retry_delay=10)
def process_video(self, job_id: str, url: str) -> None:
    ...
```

- `max_retries=2` — при технічних помилках (Gemini timeout, FFmpeg збій)
- `ValueError` (помилки бізнес-логіки: приватне відео, без субтитрів) — не ретраяться, одразу `FAILED`
- `MaxRetriesExceededError` → статус `FAILED` з повідомленням для користувача

## Celery Beat (автоочистка)

```python
beat_schedule = {
    "cleanup-old-jobs": {
        "task": "cleanup_old_jobs",
        "schedule": crontab(hour="*/6"),  # кожні 6 годин
    }
}
```

`cleanup_old_jobs` видаляє директорії у `/tmp/repurposer_jobs`, старші за `FILE_TTL_SECONDS` (24 год за замовчуванням).

## Завантаження відео (`downloader.py`)

### `get_video_info(url)`

Отримує метадані без завантаження. Перевіряє тривалість.

```python
subprocess.run(["yt-dlp", "--dump-json", "--no-playlist", safe_url], shell=False)
```

Якщо `duration > 1800` (30 хв) → `ValueError`.

### `download_video_and_transcript(url, job_dir)`

```python
subprocess.run([
    "yt-dlp",
    "--no-playlist",
    "--max-filesize", "2G",
    "--format", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]",
    "--write-auto-sub",
    "--sub-lang", "en",
    "--sub-format", "vtt",
    "--output", str(video_path),
    safe_url,
], shell=False, timeout=300)
```

**КРИТИЧНО: `shell=False` скрізь** — захист від command injection.

### `parse_vtt(vtt_path)`

Читає `.vtt` файл, видаляє:
- WEBVTT заголовок
- Timestamp рядки (`-->`)
- HTML теги (`<c>`, `<b>`, тощо)
- Цифрові індекси

Дедуплікує послідовні однакові рядки (YouTube auto-sub часто дублює).

**Повертає:** plain text рядок, готовий для Gemini промпту.

### Обробка помилок завантаження

| Ситуація | Виняток |
|---|---|
| Приватне/видалене відео | `ValueError("Відео приватне або недоступне")` |
| Відсутні субтитри | `ValueError("Субтитри не знайдено...")` |
| Відео > 30 хв | `ValueError("Відео занадто довге...")` |
| Файл > 2GB | yt-dlp `--max-filesize` відхиляє |
| Timeout > 5 хв | `subprocess.TimeoutExpired` → retry |

## Рендер (`renderer.py`)

### `find_timestamp_for_text(vtt_path, search_text)`

Шукає часову мітку для текстового фрагменту у VTT файлі.

```
Парсинг VTT → split на cue-блоки → пошук search_text[:30] у тексті блоку → повертає float секунди
```

**Fallback:** якщо текст не знайдено → `None`.

### `render_short(video_path, vtt_path, output_path, start, end)`

**Крок 1 — Вирізання кліпу:**
```bash
ffmpeg -ss {start} -i video.mp4 -t {duration} -c:v libx264 -c:a aac clip_raw.mp4
```

**Крок 2 — Масштабування у вертикальний формат:**
```bash
ffmpeg -i clip_raw.mp4 \
  -vf "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2" \
  -c:v libx264 -crf 23 -preset fast \
  -c:a aac -b:a 128k \
  short.mp4
```

Результат: **1080×1920**, 9:16 — підходить для YouTube Shorts, Instagram Reels, TikTok.

### `render_short_from_analysis(video, vtt, job_dir, analysis)`

High-level функція:
1. Бере перший момент з `analysis["moments"]`
2. Шукає timestamps через `find_timestamp_for_text`
3. Якщо не знайдено — **fallback: перші 60 секунд**
4. Викликає `render_short`

### Обробка помилок рендеру

| Ситуація | Поведінка |
|---|---|
| Timestamps не знайдено | Fallback: 0–60 сек |
| Тривалість кліпу ≤ 0 або > 120 сек | `ValueError` |
| FFmpeg помилка (crach) | RuntimeError → Celery retry |
| Недостатньо місця на диску | RuntimeError → retry |

## Структура файлів на диску

```
/tmp/repurposer_jobs/
└── {job_uuid}/
    ├── video.mp4          # Оригінальне відео
    ├── video.en.vtt       # Субтитри
    ├── clip_raw.mp4       # Проміжний файл (видаляється після)
    └── short.mp4          # ФІНАЛЬНИЙ РЕЗУЛЬТАТ
```

Вся директорія видаляється Celery beat через 24 год.

## Ліміти

| Параметр | Ліміт | Де обмежується |
|---|---|---|
| Тривалість відео | 30 хв | `downloader.py` — перевірка duration |
| Розмір файлу | 2 GB | `yt-dlp --max-filesize 2G` |
| Тривалість кліпу | max 120 сек | `renderer.py` — ValueError |
| Timeout завантаження | 5 хв | `subprocess timeout=300` |
| Timeout FFmpeg | 2 хв | `subprocess timeout=120` |
| Кількість відео / IP / день | 5 | `job_store.py` — Redis rate limit |

## Пов'язані нотатки

- [[02 — Backend і API]]
- [[04 — Gemini AI аналіз]]
- [[05 — Безпека]]
