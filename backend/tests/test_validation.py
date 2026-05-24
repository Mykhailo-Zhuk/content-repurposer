import pytest
from pydantic import ValidationError
from app.models.job import SubmitRequest


VALID_URLS = [
    "https://youtube.com/watch?v=dQw4w9WgXcQ",
    "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "https://youtu.be/dQw4w9WgXcQ",
]

INVALID_URLS = [
    "https://google.com",
    "https://youtube.com/watch",          # missing v=
    "https://youtube.com/watch?v=short",  # too short video id
    "javascript:alert(1)",                # injection attempt
    "https://evil.com/watch?v=dQw4w9WgXcQ",
    "",
    "not_a_url",
]


@pytest.mark.parametrize("url", VALID_URLS)
def test_valid_urls(url):
    req = SubmitRequest(url=url)
    assert req.url == url


@pytest.mark.parametrize("url", INVALID_URLS)
def test_invalid_urls(url):
    with pytest.raises(ValidationError):
        SubmitRequest(url=url)
