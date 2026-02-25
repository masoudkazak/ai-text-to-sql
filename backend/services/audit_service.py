from sqlalchemy.ext.asyncio import AsyncSession

from models.audit_log import AuditLog


class AuditService:
    async def log(
        self,
        db: AsyncSession,
        user_id: int,
        event_type: str,
        details: dict,
        query_request_id: int | None = None,
        ip_address: str | None = None,
    ) -> AuditLog:
        log = AuditLog(
            user_id=user_id,
            query_request_id=query_request_id,
            event_type=event_type,
            details=details,
            ip_address=ip_address,
        )
        db.add(log)
        await db.commit()
        return log
