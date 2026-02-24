from datetime import UTC, datetime

from fastapi import HTTPException, status

from core.redis_client import redis_client
from models.user import User

RATE_LIMITS = {
    "admin": {"per_minute": 6, "per_day": 20},
    "developer": {"per_minute": 4, "per_day": 12},
    "analyst": {"per_minute": 3, "per_day": 8},
    "viewer": {"per_minute": 2, "per_day": 6},
    "restricted": {"per_minute": 1, "per_day": 4},
}
AI_DAILY_LIMIT_UTC = 50


async def enforce_rate_limit(user: User) -> None:
    role = user.role.value
    limits = RATE_LIMITS[role]
    now = datetime.now(UTC)
    minute_key = f"rate:{user.id}:m:{now.strftime('%Y%m%d%H%M')}"
    day_key = f"rate:{user.id}:d:{now.strftime('%Y%m%d')}"

    minute_count = await redis_client.incr(minute_key)
    day_count = await redis_client.incr(day_key)

    if minute_count == 1:
        await redis_client.expire(minute_key, 60)
    if day_count == 1:
        await redis_client.expire(day_key, 86400)

    if minute_count > limits["per_minute"] or day_count > limits["per_day"]:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Rate limit exceeded")


async def enforce_ai_daily_limit() -> None:
    now = datetime.now(UTC)
    day_key = f"rate:ai:daily:{now.strftime('%Y%m%d')}"
    count = await redis_client.incr(day_key)

    if count == 1:
        await redis_client.expire(day_key, 86400)

    if count > AI_DAILY_LIMIT_UTC:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Global AI daily limit reached (50 per UTC day)",
        )
