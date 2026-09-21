from __future__ import annotations

import fakeredis
import pytest
from httpx import ASGITransport, AsyncClient
from redis.exceptions import ConnectionError as RedisConnectionError

from src.adapters import get_course_catalog
from src.adapters.mock.course_catalog import MockCourseCatalog
from src.core.config import get_settings
from src.core.errors import Upstream502Error
from src.core.redis import get_redis
from src.core.security import create_access_token
from src.main import app


def _auth_cookies() -> dict[str, str]:
    settings = get_settings()
    token = create_access_token(
        student_id=settings.DEMO_STUDENT_ID, username=settings.DEMO_USERNAME, role="student"
    )
    return {"session": token}


class _CountingCatalog(MockCourseCatalog):
    def __init__(self) -> None:
        super().__init__()
        self.search_calls = 0
        self.section_calls = 0

    async def search_courses(self, **kwargs):
        self.search_calls += 1
        return await super().search_courses(**kwargs)

    async def get_sections(self, code, term):
        self.section_calls += 1
        return await super().get_sections(code, term)


class _FailingCatalog:
    async def search_courses(self, **kwargs):
        raise Upstream502Error("โมดูลข้อมูลวิชา (04) ไม่ตอบสนอง", details={"module": "04"})

    async def get_sections(self, code: str, term: str):
        raise Upstream502Error("โมดูลข้อมูลวิชา (04) ไม่ตอบสนอง", details={"module": "04"})


class _BrokenRedis:
    """จำลอง Redis ล่มแบบครบทุกเมธอดที่มีการเรียกใช้จริง (cache + rate_limit ใช้ client เดียวกัน)"""

    async def get(self, key: str):
        raise RedisConnectionError("down")

    async def set(self, *args, **kwargs):
        raise RedisConnectionError("down")

    async def incr(self, key: str):
        raise RedisConnectionError("down")

    async def expire(self, *args, **kwargs):
        raise RedisConnectionError("down")


@pytest.fixture(autouse=True)
def _reset_overrides():
    yield
    app.dependency_overrides.clear()


def _client(*, authed: bool = True) -> AsyncClient:
    transport = ASGITransport(app=app)
    cookies = _auth_cookies() if authed else None
    return AsyncClient(transport=transport, base_url="http://testserver", cookies=cookies)


async def test_list_courses_success_when_logged_in() -> None:
    app.dependency_overrides[get_redis] = lambda: fakeredis.FakeAsyncRedis(decode_responses=True)
    async with _client() as client:
        response = await client.get("/api/v1/courses")

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert len(body["data"]["items"]) > 0


async def test_list_courses_without_login_returns_401() -> None:
    app.dependency_overrides[get_redis] = lambda: fakeredis.FakeAsyncRedis(decode_responses=True)
    async with _client(authed=False) as client:
        response = await client.get("/api/v1/courses")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTH_401"


async def test_list_courses_upstream_down_returns_502() -> None:
    app.dependency_overrides[get_redis] = lambda: fakeredis.FakeAsyncRedis(decode_responses=True)
    app.dependency_overrides[get_course_catalog] = lambda: _FailingCatalog()
    async with _client() as client:
        response = await client.get("/api/v1/courses")

    assert response.status_code == 502
    assert response.json()["error"]["code"] == "UPSTREAM_502"
    assert response.json()["error"]["details"]["module"] == "04"


async def test_get_sections_success_when_logged_in() -> None:
    app.dependency_overrides[get_redis] = lambda: fakeredis.FakeAsyncRedis(decode_responses=True)
    async with _client() as client:
        response = await client.get("/api/v1/courses/CPE301/sections", params={"term": "1/2569"})

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert len(body["data"]["items"]) > 0


async def test_get_sections_without_login_returns_401() -> None:
    app.dependency_overrides[get_redis] = lambda: fakeredis.FakeAsyncRedis(decode_responses=True)
    async with _client(authed=False) as client:
        response = await client.get("/api/v1/courses/CPE301/sections", params={"term": "1/2569"})

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTH_401"


async def test_get_sections_not_found_returns_404() -> None:
    app.dependency_overrides[get_redis] = lambda: fakeredis.FakeAsyncRedis(decode_responses=True)
    async with _client() as client:
        response = await client.get("/api/v1/courses/XXX999/sections", params={"term": "1/2569"})

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND_404"


async def test_get_sections_upstream_down_returns_502() -> None:
    app.dependency_overrides[get_redis] = lambda: fakeredis.FakeAsyncRedis(decode_responses=True)
    app.dependency_overrides[get_course_catalog] = lambda: _FailingCatalog()
    async with _client() as client:
        response = await client.get("/api/v1/courses/CPE301/sections", params={"term": "1/2569"})

    assert response.status_code == 502
    assert response.json()["error"]["code"] == "UPSTREAM_502"


async def test_list_courses_cache_hit_calls_adapter_once() -> None:
    fake_redis = fakeredis.FakeAsyncRedis(decode_responses=True)
    app.dependency_overrides[get_redis] = lambda: fake_redis
    catalog = _CountingCatalog()
    app.dependency_overrides[get_course_catalog] = lambda: catalog

    async with _client() as client:
        first = await client.get("/api/v1/courses", params={"limit": 5})
        second = await client.get("/api/v1/courses", params={"limit": 5})

    assert first.status_code == second.status_code == 200
    assert first.json()["data"] == second.json()["data"]
    assert catalog.search_calls == 1


async def test_get_sections_cache_hit_calls_adapter_once() -> None:
    fake_redis = fakeredis.FakeAsyncRedis(decode_responses=True)
    app.dependency_overrides[get_redis] = lambda: fake_redis
    catalog = _CountingCatalog()
    app.dependency_overrides[get_course_catalog] = lambda: catalog

    async with _client() as client:
        first = await client.get("/api/v1/courses/CPE301/sections", params={"term": "1/2569"})
        second = await client.get("/api/v1/courses/CPE301/sections", params={"term": "1/2569"})

    assert first.status_code == second.status_code == 200
    assert catalog.section_calls == 1


async def test_list_courses_redis_down_skips_cache_without_error() -> None:
    app.dependency_overrides[get_redis] = lambda: _BrokenRedis()
    catalog = _CountingCatalog()
    app.dependency_overrides[get_course_catalog] = lambda: catalog

    async with _client() as client:
        first = await client.get("/api/v1/courses", params={"limit": 5})
        second = await client.get("/api/v1/courses", params={"limit": 5})

    assert first.status_code == second.status_code == 200
    assert catalog.search_calls == 2  # cache ใช้ไม่ได้ -> เรียก adapter ทุกครั้ง ไม่ error


async def test_list_courses_pagination_returns_different_pages() -> None:
    app.dependency_overrides[get_redis] = lambda: fakeredis.FakeAsyncRedis(decode_responses=True)
    async with _client() as client:
        page1 = await client.get("/api/v1/courses", params={"limit": 3})
        next_cursor = page1.json()["data"]["next_cursor"]
        assert next_cursor is not None

        page2 = await client.get("/api/v1/courses", params={"limit": 3, "cursor": next_cursor})

    assert page1.status_code == page2.status_code == 200
    assert page1.json()["data"]["items"] != page2.json()["data"]["items"]
