from __future__ import annotations

import asyncio
import logging
import os
import sys

import asyncpg

logger = logging.getLogger(__name__)


async def wait_for_db(max_attempts: int = 60, delay_seconds: float = 1.0) -> None:
    dsn = os.getenv("DATABASE_URL", "postgresql+asyncpg://user:pass@postgres:5432/nldb")
    dsn = dsn.replace("postgresql+asyncpg://", "postgresql://")

    last_error: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            conn = await asyncpg.connect(dsn)
            await conn.close()
            logger.info("DB is ready (attempt %s/%s)", attempt, max_attempts)
            return
        except Exception as exc:  # pragma: no cover
            last_error = exc
            logger.info(
                "Waiting for DB... attempt %s/%s: %s", attempt, max_attempts, exc
            )
            await asyncio.sleep(delay_seconds)

    logger.error("Database did not become ready in time. Last error: %s", last_error)
    sys.exit(1)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s - %(message)s"
    )
    asyncio.run(wait_for_db())
