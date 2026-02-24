from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings


async def list_non_blacklisted_tables(db: AsyncSession) -> list[str]:
    result = await db.execute(
        text(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
            ORDER BY table_name
            """
        )
    )
    blacklisted = {t.lower() for t in settings.BLACKLISTED_TABLES}
    return [name for name in result.scalars().all() if name.lower() not in blacklisted]
