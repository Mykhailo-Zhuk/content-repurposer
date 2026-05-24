from enum import Enum
from pydantic import BaseModel, HttpUrl, field_validator
from typing import Optional
import re


class JobStatus(str, Enum):
    QUEUED = "queued"
    DOWNLOADING = "downloading"
    ANALYZING = "analyzing"
    RENDERING = "rendering"
    DONE = "done"
    FAILED = "failed"


class SubmitRequest(BaseModel):
    url: str

    @field_validator("url")
    @classmethod
    def validate_youtube_url(cls, v: str) -> str:
        pattern = re.compile(
            r"^https://(www\.)?("
            r"youtube\.com/watch\?v=[\w-]{11}"
            r"|youtu\.be/[\w-]{11}"
            r")"
        )
        if not pattern.match(v.strip()):
            raise ValueError("Невалідне YouTube посилання")
        return v.strip()


class SubmitResponse(BaseModel):
    job_id: str
    status: JobStatus


class JobResult(BaseModel):
    video_url: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[list[str]] = None


class JobStatusResponse(BaseModel):
    job_id: str
    status: JobStatus
    progress: int  # 0-100
    message: str
    result: Optional[JobResult] = None
    error: Optional[str] = None
