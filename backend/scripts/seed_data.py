from __future__ import annotations

import csv
import logging
from pathlib import Path

from sqlalchemy import func, select

from core.config import settings
from core.database import SessionLocal, engine
from core.security import hash_password
from models import ApprovalRequest, AuditLog, QueryRequest, TravelPlanner, User
from models.enums import UserRole

DEFAULT_LIMITS = {
    UserRole.ADMIN: 20,
    UserRole.DEVELOPER: 12,
    UserRole.ANALYST: 8,
    UserRole.VIEWER: 6,
    UserRole.RESTRICTED: 4,
}
logger = logging.getLogger(__name__)


async def seed_if_needed() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(User.metadata.create_all)
        await conn.run_sync(QueryRequest.metadata.create_all)
        await conn.run_sync(ApprovalRequest.metadata.create_all)
        await conn.run_sync(AuditLog.metadata.create_all)
        await conn.run_sync(TravelPlanner.metadata.create_all)

    async with SessionLocal() as db:
        users_count = await db.execute(select(func.count(User.id)))
        if users_count.scalar_one() == 0:
            seed_users = [
                User(
                    name="Admin",
                    email=settings.ADMIN_EMAIL,
                    hashed_password=hash_password(settings.ADMIN_PASSWORD),
                    role=UserRole.ADMIN,
                    allowed_tables=[],
                    daily_query_limit=DEFAULT_LIMITS[UserRole.ADMIN],
                ),
                User(
                    name="Analyst",
                    email="analyst@example.com",
                    hashed_password=hash_password("analyst123"),
                    role=UserRole.ANALYST,
                    allowed_tables=["travel_planner"],
                    daily_query_limit=DEFAULT_LIMITS[UserRole.ANALYST],
                ),
                User(
                    name="Developer",
                    email="developer@example.com",
                    hashed_password=hash_password("developer123"),
                    role=UserRole.DEVELOPER,
                    allowed_tables=["travel_planner"],
                    daily_query_limit=DEFAULT_LIMITS[UserRole.DEVELOPER],
                ),
                User(
                    name="Viewer",
                    email="viewer@example.com",
                    hashed_password=hash_password("viewer123"),
                    role=UserRole.VIEWER,
                    allowed_tables=["travel_planner"],
                    daily_query_limit=DEFAULT_LIMITS[UserRole.VIEWER],
                ),
                User(
                    name="Restricted",
                    email="restricted@example.com",
                    hashed_password=hash_password("restricted123"),
                    role=UserRole.RESTRICTED,
                    allowed_tables=["travel_planner"],
                    daily_query_limit=DEFAULT_LIMITS[UserRole.RESTRICTED],
                ),
            ]
            db.add_all(seed_users)
            await db.commit()

        tp_count = await db.execute(select(func.count(TravelPlanner.id)))
        if tp_count.scalar_one() == 0:
            script_path = Path(__file__).resolve()
            candidate_paths = [
                Path("/data/test.csv"),
                script_path.parents[1] / "test.csv",  # /app/test.csv in container
                Path.cwd() / "test.csv",
            ]
            csv_path = next(
                (p for p in candidate_paths if p.exists() and p.stat().st_size > 0),
                None,
            )
            if csv_path is not None:
                with csv_path.open("r", encoding="utf-8", newline="") as f:
                    reader = csv.DictReader(f)
                    rows = []
                    for i, row in enumerate(reader):
                        rows.append(
                            TravelPlanner(
                                org=row.get("org", ""),
                                dest=row.get("dest", ""),
                                days=int(row.get("days", 0) or 0),
                                date=row.get("date", ""),
                                query=row.get("query", ""),
                                level=row.get("level", ""),
                                reference_information=row.get(
                                    "reference_information", ""
                                ),
                            )
                        )
                        if len(rows) >= 1000:
                            db.add_all(rows)
                            await db.commit()
                            rows = []
                        if i >= 20000:
                            break
                    if rows:
                        db.add_all(rows)
                        await db.commit()
                logger.info("Seeded travel_planner from %s", csv_path)
            else:
                logger.info("travel_planner seed skipped: no non-empty test.csv found")


if __name__ == "__main__":
    import asyncio

    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s - %(message)s"
    )
    asyncio.run(seed_if_needed())
