from __future__ import annotations

import time

import httpx
import pytest
from jose import jwt

from src.core.config import get_settings

pytestmark = pytest.mark.db


async def _anonymous_client() -> httpx.AsyncClient:
    from src.main import app

    transport = httpx.ASGITransport(app=app)
    return httpx.AsyncClient(transport=transport, base_url="http://testserver")


async def test_login_success_sets_httponly_cookie_and_no_token_in_body(seeded_demo_student) -> None:
    settings = get_settings()
    async with await _anonymous_client() as client:
        response = await client.post(
            "/api/v1/auth/login",
            json={"username": settings.DEMO_USERNAME, "password": settings.DEMO_PASSWORD},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["data"] == {
        "username": settings.DEMO_USERNAME,
        "student_id": settings.DEMO_STUDENT_ID,
        "role": "student",
    }
    assert "token" not in body["data"]

    set_cookie = response.headers.get("set-cookie", "")
    assert "session=" in set_cookie
    assert "HttpOnly" in set_cookie


async def test_login_wrong_password_returns_401(seeded_demo_student) -> None:
    settings = get_settings()
    async with await _anonymous_client() as client:
        response = await client.post(
            "/api/v1/auth/login",
            json={"username": settings.DEMO_USERNAME, "password": "รหัสผิดแน่นอน"},
        )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTH_401"


async def test_login_wrong_username_returns_same_message_as_wrong_password(seeded_demo_student) -> None:
    settings = get_settings()
    async with await _anonymous_client() as client:
        wrong_username = await client.post(
            "/api/v1/auth/login",
            json={"username": "ไม่มีบัญชีนี้", "password": settings.DEMO_PASSWORD},
        )
        wrong_password = await client.post(
            "/api/v1/auth/login",
            json={"username": settings.DEMO_USERNAME, "password": "ผิดแน่นอน"},
        )

    assert wrong_username.status_code == wrong_password.status_code == 401
    assert wrong_username.json()["error"]["message"] == wrong_password.json()["error"]["message"]


async def test_me_without_cookie_returns_401(db_session) -> None:
    async with await _anonymous_client() as client:
        response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTH_401"


async def test_me_with_expired_token_returns_401(seeded_demo_student) -> None:
    settings = get_settings()
    now = int(time.time())
    expired_token = jwt.encode(
        {
            "sub": settings.DEMO_STUDENT_ID,
            "username": settings.DEMO_USERNAME,
            "role": "student",
            "iat": now - 120,
            "exp": now - 60,
        },
        settings.JWT_SECRET,
        algorithm="HS256",
    )
    async with await _anonymous_client() as client:
        client.cookies.set("session", expired_token)
        response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401


async def test_me_with_forged_token_returns_401(db_session) -> None:
    async with await _anonymous_client() as client:
        client.cookies.set("session", "this.is-not.valid")
        response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401


async def test_me_returns_profile_when_logged_in(logged_in_client) -> None:
    settings = get_settings()
    response = await logged_in_client.get("/api/v1/auth/me")
    assert response.status_code == 200
    body = response.json()
    assert body["data"]["student_id"] == settings.DEMO_STUDENT_ID
    assert body["data"]["username"] == settings.DEMO_USERNAME


async def test_logout_clears_cookie_and_session_stops_working(logged_in_client) -> None:
    response = await logged_in_client.post("/api/v1/auth/logout")
    assert response.status_code == 200

    me_response = await logged_in_client.get("/api/v1/auth/me")
    assert me_response.status_code == 401


async def test_logout_response_envelope_ok_true(logged_in_client) -> None:
    response = await logged_in_client.post("/api/v1/auth/logout")
    assert response.status_code == 200
    assert response.json()["ok"] is True


async def test_logout_without_login_still_returns_200(db_session) -> None:
    async with await _anonymous_client() as client:
        response = await client.post("/api/v1/auth/logout")
    assert response.status_code == 200
