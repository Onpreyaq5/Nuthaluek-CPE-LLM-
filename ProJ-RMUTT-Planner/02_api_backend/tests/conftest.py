from __future__ import annotations

import os
from pathlib import Path

import pytest

from src.core.asyncio_compat import ensure_selector_event_loop_policy_on_windows

ensure_selector_event_loop_policy_on_windows()

# ต้องตั้งก่อน import อะไรจาก src.core.config (lru_cache) เพื่อให้ทุก test ต่อ TEST_DATABASE_URL แทน DATABASE_URL ปกติ
if os.getenv("TEST_DATABASE_URL"):
    os.environ["DATABASE_URL"] = os.environ["TEST_DATABASE_URL"]


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if os.getenv("TEST_DATABASE_URL"):
        return
    skip_db = pytest.mark.skip(reason="ต้องตั้ง TEST_DATABASE_URL (Postgres) ก่อนรัน test กลุ่มนี้")
    for item in items:
        if "db" in item.keywords:
            item.add_marker(skip_db)


@pytest.fixture(autouse=True)
def _default_fake_redis():
    """ทุก test ต่อ fakeredis แทน Redis จริงเป็นค่าเริ่มต้นเสมอ (cache และ rate_limit ใช้ get_redis
    ตัวเดียวกัน) กัน test พยายามต่อ Redis จริงที่ไม่มีอยู่จนค้าง (rate_limit เป็น dependency ที่ทำงานกับ
    ทุก request ใต้ /api/v1 ตั้งแต่ Prompt 10) — test ไหนต้องการ override เป็นอย่างอื่น (เช่น จำลอง Redis
    ล่ม) ทำได้ตามปกติ เพราะ override ทีหลังในตัว test เองจะทับค่านี้ (autouse fixture ตั้งค่าก่อนเสมอ
    ตามกติกาของ pytest: autouse ทำงานก่อน fixture อื่นที่ scope เดียวกัน)
    """
    import fakeredis

    from src.core.redis import get_redis
    from src.main import app

    app.dependency_overrides[get_redis] = lambda: fakeredis.FakeAsyncRedis(decode_responses=True)
    yield
    app.dependency_overrides.pop(get_redis, None)


@pytest.fixture(scope="session")
def _db_schema():
    """สร้าง schema ด้วย alembic upgrade head ครั้งเดียวต่อ session ของ pytest"""
    if not os.getenv("TEST_DATABASE_URL"):
        yield
        return

    from alembic import command
    from alembic.config import Config

    from src.core.config import get_settings
    from src.core.db import get_engine, get_sessionmaker

    get_settings.cache_clear()
    get_engine.cache_clear()
    get_sessionmaker.cache_clear()

    root = Path(__file__).resolve().parents[1]
    cfg = Config(str(root / "alembic.ini"))
    cfg.set_main_option("script_location", str(root / "migrations"))
    command.upgrade(cfg, "head")
    yield


@pytest.fixture
async def db_session(_db_schema):
    """เคลียร์ตารางที่ 02 เป็นเจ้าของก่อนทุก test แล้วคืน session เดียวกันให้ใช้ต่อ"""
    from sqlalchemy import text

    from src.core.db import get_sessionmaker

    session_factory = get_sessionmaker()
    async with session_factory() as session:
        await session.execute(
            text(
                "TRUNCATE TABLE plan_items, plans, student_preferences, students "
                "RESTART IDENTITY CASCADE"
            )
        )
        await session.commit()
        yield session


@pytest.fixture
async def seeded_demo_student(db_session):
    """สร้างบัญชีเดโมตาม DEMO_STUDENT_ID/DEMO_USERNAME ในฐานข้อมูลเทสต์"""
    from src.core.config import get_settings
    from src.models import Student, StudentPreference

    settings = get_settings()
    db_session.add(
        Student(student_id=settings.DEMO_STUDENT_ID, username=settings.DEMO_USERNAME, role="student")
    )
    db_session.add(
        StudentPreference(
            student_id=settings.DEMO_STUDENT_ID, free_days=["FRI"], no_early_class=False, max_credits=21
        )
    )
    await db_session.commit()


@pytest.fixture
async def second_student(db_session):
    """นักศึกษาอีกคนที่ไม่ใช่บัญชีเดโม ใช้ทดสอบ ownership (คนอื่นเข้าถึงของฉันไม่ได้)"""
    from src.core.security import create_access_token
    from src.models import Student

    student_id = "6500000099"
    username = "second_user"
    db_session.add(Student(student_id=student_id, username=username, role="student"))
    await db_session.commit()

    token = create_access_token(student_id=student_id, username=username, role="student")
    return {"student_id": student_id, "username": username, "token": token}


@pytest.fixture
async def logged_in_client(seeded_demo_student):
    """httpx.AsyncClient ที่ล็อกอินด้วยบัญชีเดโมแล้ว (มี cookie session ติดตัว)"""
    import httpx

    from src.core.config import get_settings
    from src.main import app

    settings = get_settings()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/api/v1/auth/login",
            json={"username": settings.DEMO_USERNAME, "password": settings.DEMO_PASSWORD},
        )
        assert response.status_code == 200
        yield client
