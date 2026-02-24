from __future__ import annotations

import asyncio
import os
import sys

import asyncpg


async def wait_for_db(max_attempts: int = 60, delay_seconds: float = 1.0) -> None:
    dsn = os.getenv("DATABASE_URL", "postgresql+asyncpg://user:pass@postgres:5432/nldb")
    dsn = dsn.replace("postgresql+asyncpg://", "postgresql://")

    last_error: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            conn = await asyncpg.connect(dsn)
            await conn.close()
            print(f"DB is ready (attempt {attempt}/{max_attempts})")
            return
        except Exception as exc:  # pragma: no cover
            last_error = exc
            print(f"Waiting for DB... attempt {attempt}/{max_attempts}: {exc}")
            await asyncio.sleep(delay_seconds)

    print(f"Database did not become ready in time. Last error: {last_error}")
    sys.exit(1)


if __name__ == "__main__":
    asyncio.run(wait_for_db())
