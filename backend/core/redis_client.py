from redis.asyncio import Redis

from core.config import settings


redis_client: Redis | None = None


def get_redis_client() -> Redis:
    if redis_client is None:
        raise RuntimeError(
            "Redis client not initialized. Make sure to initialize in app lifespan."
        )
    return redis_client


async def init_redis():
    global redis_client
    redis_client = Redis.from_url(settings.REDIS_URL, decode_responses=True)


async def close_redis():
    global redis_client
    if redis_client:
        await redis_client.close()
        redis_client = None
