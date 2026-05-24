# Content Repurposer 🎬

> Автоматична нарізка YouTube відео на Shorts/Reels за допомогою AI

## Структура

```
content-repurposer/
├── frontend/          # Next.js 14 + TypeScript + Tailwind
├── backend/           # FastAPI + Celery + Redis
├── docker/            # Docker configs
├── docker-compose.yml
└── .env.example
```

## Швидкий старт

### Вимоги
- Docker & Docker Compose
- Node.js 20+
- Python 3.11+

### Запуск через Docker (рекомендовано)

```bash
cp .env.example .env
# заповни .env своїми ключами
docker compose up --build
```

### Локальний запуск

**Backend:**
```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
# окремо: celery -A app.workers.celery_app worker --loglevel=info
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

## Сервіси

| Сервіс | URL |
|---|---|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |
| Redis | localhost:6379 |

## Змінні оточення

Дивись `.env.example` — усі ключі описані з коментарями.

## Ліцензія

MIT
