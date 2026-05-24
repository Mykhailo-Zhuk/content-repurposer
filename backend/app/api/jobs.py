import uuid
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import FileResponse
from pathlib import Path

from app.core.config import get_settings
from app.core.job_store import (
    create_job,
    get_job,
    get_user_job_count,
    increment_user_job_count,
)
from app.models.job import SubmitRequest, SubmitResponse, JobStatusResponse
from app.workers.celery_app import process_video

router = APIRouter(prefix="/api/jobs", tags=["jobs"])
settings = get_settings()


def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@router.post("/", response_model=SubmitResponse)
async def submit_job(body: SubmitRequest, request: Request) -> SubmitResponse:
    """Submit a YouTube URL for processing."""
    ip = get_client_ip(request)

    # Rate limit check
    count = get_user_job_count(ip)
    if count >= settings.rate_limit_per_day:
        raise HTTPException(
            status_code=429,
            detail=f"Ліміт на сьогодні вичерпано ({settings.rate_limit_per_day} відео). Спробуйте завтра.",
        )

    job_id = str(uuid.uuid4())
    create_job(job_id)
    increment_user_job_count(ip)

    # Enqueue Celery task
    process_video.delay(job_id, body.url)

    return SubmitResponse(job_id=job_id, status="queued")


@router.get("/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str) -> JobStatusResponse:
    """Poll job status."""
    # Validate job_id format to prevent path traversal
    try:
        uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid job ID")

    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return job


@router.get("/{job_id}/download")
async def download_result(job_id: str) -> FileResponse:
    """Download the rendered short video."""
    try:
        uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid job ID")

    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status != "done":
        raise HTTPException(status_code=400, detail="Job not finished yet")

    # Resolve path safely (prevent path traversal)
    storage = Path(settings.local_storage_path).resolve()
    short_path = (storage / job_id / "short.mp4").resolve()

    if not str(short_path).startswith(str(storage)):
        raise HTTPException(status_code=400, detail="Invalid path")

    if not short_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(
        path=str(short_path),
        media_type="video/mp4",
        filename=f"short_{job_id[:8]}.mp4",
    )
