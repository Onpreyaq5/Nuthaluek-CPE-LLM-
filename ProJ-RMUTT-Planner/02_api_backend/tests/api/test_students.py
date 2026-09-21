from __future__ import annotations

import httpx
import pytest

from src.adapters import get_student_data
from src.core.config import get_settings
from src.core.errors import Upstream502Error
from src.core.security import create_access_token
from src.main import app


class _FailingStudentData:
    async def get_context(self, student_id: str):
        raise Upstream502Error("โมดูลข้อมูลนักศึกษา (05) ไม่ตอบสนอง", details={"module": "05"})

    async def get_transcript(self, student_id: str):
        raise Upstream502Error("โมดูลข้อมูลนักศึกษา (05) ไม่ตอบสนอง", details={"module": "05"})

    async def import_graduate_check(self, raw: bytes):
        raise Upstream502Error("โมดูลข้อมูลนักศึกษา (05) ไม่ตอบสนอง", details={"module": "05"})


@pytest.fixture(autouse=True)
def _reset_overrides():
    yield
    app.dependency_overrides.clear()


def _client(*, authed: bool = True) -> httpx.AsyncClient:
    transport = httpx.ASGITransport(app=app)
    cookies = None
    if authed:
        settings = get_settings()
        token = create_access_token(
            student_id=settings.DEMO_STUDENT_ID, username=settings.DEMO_USERNAME, role="student"
        )
        cookies = {"session": token}
    return httpx.AsyncClient(transport=transport, base_url="http://testserver", cookies=cookies)


@pytest.mark.db
async def test_get_profile_success(seeded_demo_student) -> None:
    async with _client() as client:
        response = await client.get("/api/v1/students/me/profile")

    assert response.status_code == 200
    body = response.json()["data"]
    assert body["student_id"] == get_settings().DEMO_STUDENT_ID
    assert body["program_name"]
    assert body["gpax"] > 0


@pytest.mark.db
async def test_get_profile_without_login_returns_401() -> None:
    async with _client(authed=False) as client:
        response = await client.get("/api/v1/students/me/profile")
    assert response.status_code == 401


@pytest.mark.db
async def test_get_profile_upstream_down_returns_502(seeded_demo_student) -> None:
    app.dependency_overrides[get_student_data] = lambda: _FailingStudentData()
    async with _client() as client:
        response = await client.get("/api/v1/students/me/profile")
    assert response.status_code == 502
    assert response.json()["error"]["code"] == "UPSTREAM_502"


async def test_get_transcript_success() -> None:
    async with _client() as client:
        response = await client.get("/api/v1/students/me/transcript")

    assert response.status_code == 200
    body = response.json()["data"]
    assert len(body["courses"]) > 0
    assert body["credits_by_category"]


async def test_get_transcript_without_login_returns_401() -> None:
    async with _client(authed=False) as client:
        response = await client.get("/api/v1/students/me/transcript")
    assert response.status_code == 401


async def test_get_transcript_upstream_down_returns_502() -> None:
    app.dependency_overrides[get_student_data] = lambda: _FailingStudentData()
    async with _client() as client:
        response = await client.get("/api/v1/students/me/transcript")
    assert response.status_code == 502


async def test_import_success() -> None:
    html = "<html><body>ผลการเรียน</body></html>".encode()
    async with _client() as client:
        response = await client.post(
            "/api/v1/students/me/import", files={"file": ("transcript.html", html, "text/html")}
        )

    assert response.status_code == 200
    body = response.json()["data"]
    assert body["imported_courses"] > 0


async def test_import_without_login_returns_401() -> None:
    html = b"<html></html>"
    async with _client(authed=False) as client:
        response = await client.post(
            "/api/v1/students/me/import", files={"file": ("transcript.html", html, "text/html")}
        )
    assert response.status_code == 401


async def test_import_file_too_large_returns_413() -> None:
    huge_html = b"<html>" + b"x" * (2 * 1024 * 1024 + 1)
    async with _client() as client:
        response = await client.post(
            "/api/v1/students/me/import", files={"file": ("transcript.html", huge_html, "text/html")}
        )
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "PAYLOAD_413"


async def test_import_non_html_content_returns_422() -> None:
    not_html = b"this is just plain text, not a real transcript file at all"
    async with _client() as client:
        response = await client.post(
            "/api/v1/students/me/import",
            files={"file": ("transcript.txt", not_html, "text/html")},
        )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_422"


async def test_import_ignores_declared_content_type_and_extension() -> None:
    # ไฟล์นามสกุล .html และ content-type text/html แต่เนื้อหาจริงไม่ใช่ HTML เลย -> ต้องยังโดน 422
    not_html = b"just some random bytes pretending to be html by extension only"
    async with _client() as client:
        response = await client.post(
            "/api/v1/students/me/import", files={"file": ("fake.html", not_html, "text/html")}
        )
    assert response.status_code == 422
