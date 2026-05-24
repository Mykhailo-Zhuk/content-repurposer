import json
import redis
from app.core.config import get_settings
from app.models.job import JobStatus, JobStatusResponse, JobResult
from typing import Optional

settings = get_settings()
_redis = redis.from_url(settings.redis_url, decode_responses=True)

JOB_TTL = 60 * 60 * 24  # 24 hours


def create_job(job_id: str) -> None:
    data = {
        "job_id": job_id,
        "status": JobStatus.QUEUED,
        "progress": 0,
        "message": "У черзі",
        "result": None,
        "error": None,
    }
    _redis.setex(f"job:{job_id}", JOB_TTL, json.dumps(data))


def update_job(
    job_id: str,
    status: JobStatus,
    progress: int,
    message: str,
    result: Optional[dict] = None,
    error: Optional[str] = None,
) -> None:
    existing = get_job_raw(job_id)
    if not existing:
        return
    existing.update(
        status=status,
        progress=progress,
        message=message,
        result=result,
        error=error,
    )
    _redis.setex(f"job:{job_id}", JOB_TTL, json.dumps(existing))


def get_job_raw(job_id: str) -> Optional[dict]:
    raw = _redis.get(f"job:{job_id}")
    if not raw:
        return None
    return json.loads(raw)


def get_job(job_id: str) -> Optional[JobStatusResponse]:
    raw = get_job_raw(job_id)
    if not raw:
        return None
    result = None
    if raw.get("result"):
        result = JobResult(**raw["result"])
    return JobStatusResponse(
        job_id=raw["job_id"],
        status=raw["status"],
        progress=raw["progress"],
        message=raw["message"],
        result=result,
        error=raw.get("error"),
    )


def get_user_job_count(ip: str) -> int:
    return int(_redis.get(f"ratelimit:{ip}") or 0)


def increment_user_job_count(ip: str) -> None:
    pipe = _redis.pipeline()
    pipe.incr(f"ratelimit:{ip}")
    pipe.expire(f"ratelimit:{ip}", 86400)  # reset daily
    pipe.execute()
