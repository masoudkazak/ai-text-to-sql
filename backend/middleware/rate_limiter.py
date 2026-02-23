"""Redis-backed per-minute/per-day rate limiter."""

from datetime import UTC, datetime

from fastapi import HTTPException, status

from core.redis_client import redis_client
from models.user import User

RATE_LIMITS = {
    "admin": {"per_minute": 30, "per_day": 500},
    "developer": {"per_minute": 20, "per_day": 300},
    "analyst": {"per_minute": 15, "per_day": 200},
    "viewer": {"per_minute": 10, "per_day": 100},
    "restricted": {"per_minute": 5, "per_day": 50},
}


async def enforce_rate_limit(user: User) -> None:
    """Raise 429 when user exceeds role limits."""

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
