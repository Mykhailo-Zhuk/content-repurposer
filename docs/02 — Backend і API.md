---
tags: [ope-167, backend, fastapi, celery, redis, api]
created: 2026-05-17
status: active
relates-to: "[[00 — OPE-167 Огляд проекту]]"
---

# 02 — Backend і API

## Технологічний стек

| Компонент | Технологія | Призначення |
|---|---|---|
| Web framework | FastAPI 0.111 | HTTP API, валідація, документація |
| Черга задач | Celery 5.4 | Async обробка відео |
| State storage | Redis 7 | Зберігання статусів job, rate limiting |
| Моделі | Pydantic v2 | Валідація вхідних даних і відповідей |
| Налаштування | pydantic-settings | Конфіг через env variables |
| Сервер | Uvicorn | ASGI сервер |

## Структура

```
backend/app/
├── main.py           # FastAPI app, CORS middleware, роутери
├── api/
│   └── jobs.py       # POST /api/jobs/, GET /api/jobs/{id}, GET /api/jobs/{id}/download
├── core/
│   ├── config.py     # Settings (pydantic-settings)
│   └── job_store.py  # Redis: create/update/get job, rate limiting
├── models/
│   └── job.py        # SubmitRequest, JobStatusResponse, JobResult, JobStatus enum
├── services/
│   ├── downloader.py # yt-dlp wrapper + VTT парсер
│   ├── ai_analyzer.py # Gemini API інтеграція
│   └── renderer.py   # FFmpeg wrapper
└── workers/
    └── celery_app.py # Celery app + process_video task + cleanup_old_jobs
```

## API ендпоінти

### `POST /api/jobs/`

Прийом YouTube посилання, постановка задачі в чергу.

**Request body:**
```json
{ "url": "https://youtube.com/watch?v=dQw4w9WgXcQ" }
```

**Response 200:**
```json
{ "job_id": "uuid-v4", "status": "queued" }
```

**Помилки:**
| Код | Причина |
|---|---|
| 422 | Невалідний URL (Pydantic/Zod відхилив) |
| 429 | Rate limit перевищено |

---

### `GET /api/jobs/{job_id}`

Polling статусу задачі.

**Response 200:**
```json
{
  "job_id": "uuid-v4",
  "status": "rendering",
  "progress": 75,
  "message": "Рендер відео...",
  "result": null,
  "error": null
}
```

**Після завершення (`status: "done"`):**
```json
{
  "status": "done",
  "progress": 100,
  "message": "Готово!",
  "result": {
    "video_url": "/api/jobs/{id}/download",
    "title": "Заголовок короткого відео",
    "description": "Опис для соцмереж",
    "tags": ["tag1", "tag2", "tag3"]
  }
}
```

**Помилки:**
| Код | Причина |
|---|---|
| 400 | Невалідний UUID формат job_id |
| 404 | Job не знайдено (або TTL минув) |

---

### `GET /api/jobs/{job_id}/download`

Завантаження готового відео.

**Response:** FileResponse, `Content-Type: video/mp4`, `filename: short_{id[:8]}.mp4`

**Помилки:**
| Код | Причина |
|---|---|
| 400 | Job ще не завершено або невалідний UUID |
| 404 | Файл не знайдено на диску |

---

### `GET /health`

Healthcheck для Docker/load balancer.

**Response:** `{ "status": "ok" }`

## Моделі (Pydantic)

### `JobStatus` (Enum)

```python
class JobStatus(str, Enum):
    QUEUED = "queued"
    DOWNLOADING = "downloading"
    ANALYZING = "analyzing"
    RENDERING = "rendering"
    DONE = "done"
    FAILED = "failed"
```

### `SubmitRequest`

```python
class SubmitRequest(BaseModel):
    url: str

    @field_validator("url")
    def validate_youtube_url(cls, v):
        # Whitelist regex — єдина точка валідації
        pattern = r"^https://(www\.)?(youtube\.com/watch\?v=[\w-]{11}|youtu\.be/[\w-]{11})"
        if not re.match(pattern, v.strip()):
            raise ValueError("Невалідне YouTube посилання")
        return v.strip()
```

### `JobStatusResponse`

```python
class JobStatusResponse(BaseModel):
    job_id: str
    status: JobStatus
    progress: int        # 0–100
    message: str
    result: Optional[JobResult] = None
    error: Optional[str] = None
```

## Redis — структура ключів

| Ключ | TTL | Значення |
|---|---|---|
| `job:{uuid}` | 24 год | JSON: статус, прогрес, результат |
| `ratelimit:{ip}` | 24 год | int: кількість запитів за день |

## Конфігурація (`config.py`)

```python
class Settings(BaseSettings):
    gemini_api_key: str = ""
    redis_url: str = "redis://localhost:6379/0"
    secret_key: str = ""
    cors_origins: list[str] = ["http://localhost:3000"]
    storage_backend: str = "local"   # "local" | "s3"
    local_storage_path: str = "/tmp/repurposer_jobs"
    file_ttl_seconds: int = 86400    # 24 год
    rate_limit_per_day: int = 5
```

Всі значення читаються з `.env` через `pydantic-settings`.

## Rate Limiting

Реалізований вручну через Redis (без slowapi):

```python
count = get_user_job_count(ip)       # INCR ratelimit:{ip}
if count >= settings.rate_limit_per_day:
    raise HTTPException(429, "Ліміт вичерпано")
increment_user_job_count(ip)          # expire = 86400 сек
```

IP визначається через `X-Forwarded-For` (для роботи за reverse proxy).

## CORS

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,  # з .env
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
```

## Обробка помилок у роутері

| Тип помилки | HTTP статус | Поведінка |
|---|---|---|
| `ValidationError` (Pydantic) | 422 | Авто FastAPI |
| Невалідний UUID | 400 | `HTTPException` |
| Job не знайдено | 404 | `HTTPException` |
| Rate limit | 429 | `HTTPException` з описом |
| Path traversal | 400 | Перевірка `str.startswith` |

## Автодокументація

Після запуску доступна за адресою:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Пов'язані нотатки

- [[01 — Frontend]]
- [[03 — Pipeline обробки відео]]
- [[05 — Безпека]]
