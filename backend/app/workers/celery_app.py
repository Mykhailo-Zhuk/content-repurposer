from celery import Celery
from celery.schedules import crontab
from app.core.config import get_settings
from app.core.job_store import update_job, get_job_raw
from app.models.job import JobStatus
from app.services.downloader import download_video_and_transcript, parse_vtt
from app.services.ai_analyzer import analyze_transcript
from app.services.renderer import render_short_from_analysis
from pathlib import Path
import shutil
import time

settings = get_settings()

celery_app = Celery(
    "repurposer",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    beat_schedule={
        "cleanup-old-jobs": {
            "task": "app.workers.celery_app.cleanup_old_jobs",
            "schedule": crontab(minute=0, hour="*/6"),  # every 6 hours
        },
    },
)


@celery_app.task(bind=True, max_retries=2, default_retry_delay=10)
def process_video(self, job_id: str, url: str) -> None:
    """Main pipeline: download → analyze → render."""
    job_dir = Path(settings.local_storage_path) / job_id

    try:
        # Step 1: Download
        update_job(job_id, JobStatus.DOWNLOADING, 10, "Завантаження відео...")
        files = download_video_and_transcript(url, job_dir)

        # Step 2: Parse transcript
        update_job(job_id, JobStatus.ANALYZING, 40, "Аналіз transcript...")
        transcript = parse_vtt(files["subtitle_path"])

        # Step 3: AI analysis
        update_job(job_id, JobStatus.ANALYZING, 60, "AI шукає кращі моменти...")
        analysis = analyze_transcript(transcript)

        # Step 4: Render
        update_job(job_id, JobStatus.RENDERING, 75, "Рендер відео...")
        short_path = render_short_from_analysis(
            files["video_path"],
            files["subtitle_path"],
            str(job_dir),
            analysis,
        )

        # Step 5: Done
        result = {
            "video_url": f"/api/jobs/{job_id}/download",
            "title": analysis.get("title", ""),
            "description": analysis.get("description", ""),
            "tags": analysis.get("tags", []),
        }
        update_job(job_id, JobStatus.DONE, 100, "Готово!", result=result)

    except ValueError as e:
        # User-facing errors (bad URL, no subtitles, too long)
        update_job(job_id, JobStatus.FAILED, 0, str(e), error=str(e))

    except Exception as exc:
        # Retryable errors
        try:
            raise self.retry(exc=exc)
        except self.MaxRetriesExceededError:
            msg = "Помилка обробки. Спробуйте ще раз пізніше."
            update_job(job_id, JobStatus.FAILED, 0, msg, error=str(exc))


@celery_app.task
def cleanup_old_jobs() -> None:
    """Delete job directories older than FILE_TTL_SECONDS."""
    storage = Path(settings.local_storage_path)
    if not storage.exists():
        return

    now = time.time()
    ttl = settings.file_ttl_seconds

    for job_dir in storage.iterdir():
        if not job_dir.is_dir():
            continue
        age = now - job_dir.stat().st_mtime
        if age > ttl:
            shutil.rmtree(job_dir, ignore_errors=True)
