from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from redis.asyncio import Redis

from src.adapters import get_course_catalog
from src.adapters.interfaces import CourseCatalog
from src.api.deps import CurrentUser, current_user
from src.core.cache import cache_get_json, cache_set_json, make_cache_key
from src.core.envelope import success_envelope
from src.core.redis import get_redis
from src.schemas.common import Day
from src.schemas.courses import CourseListResponse, SectionListResponse
from src.schemas.envelope import SuccessEnvelope

router = APIRouter(prefix="/courses", tags=["courses"])

_CACHE_TTL_SECONDS = 600  # 10 นาที ตาม PLAN.md


@router.get("", response_model=SuccessEnvelope[CourseListResponse])
async def list_courses(
    q: str | None = None,
    term: str | None = None,
    day: Day | None = None,
    teacher: str | None = None,
    cursor: str | None = None,
    limit: int = Query(default=20, le=100),
    user: CurrentUser = Depends(current_user),
    catalog: CourseCatalog = Depends(get_course_catalog),
    redis: Redis = Depends(get_redis),
) -> dict:
    cache_key = make_cache_key(
        "courses:list",
        {
            "q": q,
            "term": term,
            "day": day.value if day else None,
            "teacher": teacher,
            "cursor": cursor,
            "limit": limit,
        },
    )

    cached = await cache_get_json(redis, cache_key)
    if cached is not None:
        return success_envelope(cached)

    result = await catalog.search_courses(
        q=q, term=term, day=day, teacher=teacher, cursor=cursor, limit=limit
    )
    data = result.model_dump(mode="json")
    await cache_set_json(redis, cache_key, data, _CACHE_TTL_SECONDS)
    return success_envelope(data)


@router.get("/{code}/sections", response_model=SuccessEnvelope[SectionListResponse])
async def list_sections(
    code: str,
    term: str,
    user: CurrentUser = Depends(current_user),
    catalog: CourseCatalog = Depends(get_course_catalog),
    redis: Redis = Depends(get_redis),
) -> dict:
    cache_key = make_cache_key("courses:sections", {"code": code, "term": term})

    cached = await cache_get_json(redis, cache_key)
    if cached is not None:
        return success_envelope(cached)

    result = await catalog.get_sections(code, term)
    data = result.model_dump(mode="json")
    await cache_set_json(redis, cache_key, data, _CACHE_TTL_SECONDS)
    return success_envelope(data)
