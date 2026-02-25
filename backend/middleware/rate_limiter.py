from datetime import UTC, datetime

from fastapi import HTTPException, status

from core.redis_client import get_redis_client
from models.enums import UserRole
from models.user import User

RATE_LIMITS = {
    "admin": {"per_minute": 6, "per_day": 20},
    "developer": {"per_minute": 4, "per_day": 12},
    "analyst": {"per_minute": 3, "per_day": 8},
    "viewer": {"per_minute": 2, "per_day": 6},
    "restricted": {"per_minute": 1, "per_day": 4},
}
AI_DAILY_LIMIT_UTC = 50


def _user_day_key(user_id: int, now: datetime) -> str:
    return f"rate:{user_id}:d:{now.strftime('%Y%m%d')}"


def _user_minute_key(user_id: int, now: datetime) -> str:
    return f"rate:{user_id}:m:{now.strftime('%Y%m%d%H%M')}"


def _ip_day_key(ip: str, now: datetime) -> str:
    return f"rate:ip:{ip}:d:{now.strftime('%Y%m%d')}"


def _ip_minute_key(ip: str, now: datetime) -> str:
    return f"rate:ip:{ip}:m:{now.strftime('%Y%m%d%H%M')}"


def _global_day_key(now: datetime) -> str:
    return f"rate:ai:daily:{now.strftime('%Y%m%d')}"


async def enforce_rate_limit(user: User, client_ip: str | None = None) -> None:
    role = user.role.value
    limits = RATE_LIMITS[role]
    now = datetime.now(UTC)
    redis = get_redis_client()

    if user.role == UserRole.VIEWER and client_ip:
        minute_key = _ip_minute_key(client_ip, now)
        day_key = _ip_day_key(client_ip, now)
    else:
        minute_key = _user_minute_key(user.id, now)
        day_key = _user_day_key(user.id, now)

    minute_count = await redis.incr(minute_key)
    day_count = await redis.incr(day_key)

    if minute_count == 1:
        await redis.expire(minute_key, 60)
    if day_count == 1:
        await redis.expire(day_key, 86400)

    if minute_count > limits["per_minute"] or day_count > limits["per_day"]:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Rate limit exceeded")


async def enforce_ai_daily_limit() -> None:
    now = datetime.now(UTC)
    day_key = _global_day_key(now)
    redis = get_redis_client()
    count = await redis.incr(day_key)

    if count == 1:
        await redis.expire(day_key, 86400)

    if count > AI_DAILY_LIMIT_UTC:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Global AI daily limit reached (50 per UTC day)",
        )


async def get_user_daily_usage(user: User, client_ip: str | None = None) -> tuple[int, int, int]:
    now = datetime.now(UTC)
    redis = get_redis_client()
    
    if user.role == UserRole.VIEWER and client_ip:
        day_key = _ip_day_key(client_ip, now)
        limit = RATE_LIMITS["viewer"]["per_day"]
    else:
        day_key = _user_day_key(user.id, now)
        limit = max(1, user.daily_query_limit)
    
    used = int(await redis.get(day_key) or 0)
    remaining = max(0, limit - used)
    return limit, used, remaining


async def get_global_daily_usage() -> tuple[int, int, int]:
    now = datetime.now(UTC)
    day_key = _global_day_key(now)
    redis = get_redis_client()
    used = int(await redis.get(day_key) or 0)
    remaining = max(0, AI_DAILY_LIMIT_UTC - used)
    return AI_DAILY_LIMIT_UTC, used, remaining
