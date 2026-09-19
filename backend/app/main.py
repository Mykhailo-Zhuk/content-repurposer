from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import get_settings
from app.api.jobs import router as jobs_router

settings = get_settings()

app = FastAPI(
    title="Content Repurposer API",
    description="Автоматична нарізка YouTube відео на Shorts/Reels за допомогою AI",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(jobs_router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
