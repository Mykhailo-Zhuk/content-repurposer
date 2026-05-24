import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_submit_invalid_url():
    response = client.post("/api/jobs/", json={"url": "https://google.com"})
    assert response.status_code == 422


def test_submit_valid_youtube_url(monkeypatch):
    """Test submit with mocked Redis and Celery."""
    import app.api.jobs as jobs_module

    monkeypatch.setattr(jobs_module, "create_job", lambda job_id: None)
    monkeypatch.setattr(jobs_module, "get_user_job_count", lambda ip: 0)
    monkeypatch.setattr(jobs_module, "increment_user_job_count", lambda ip: None)

    from app.workers import celery_app as celery_module
    monkeypatch.setattr(celery_module.process_video, "delay", lambda *a, **kw: None)

    response = client.post(
        "/api/jobs/",
        json={"url": "https://youtube.com/watch?v=dQw4w9WgXcQ"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "job_id" in data
    assert data["status"] == "queued"


def test_get_nonexistent_job(monkeypatch):
    import uuid
    import app.api.jobs as jobs_module
    monkeypatch.setattr(jobs_module, "get_job", lambda job_id: None)
    response = client.get(f"/api/jobs/{uuid.uuid4()}")
    assert response.status_code == 404


def test_get_invalid_job_id():
    response = client.get("/api/jobs/not-a-uuid")
    assert response.status_code == 400
