"""Audit endpoints."""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.security import get_current_user
from models.audit_log import AuditLog
from models.enums import UserRole
from models.user import User
from schemas.audit import AuditOut

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("", response_model=list[AuditOut])
async def list_audit_logs(
    user_id: int | None = Query(default=None),
    event_type: str | None = Query(default=None),
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current: User = Depends(get_current_user),
) -> list[AuditOut]:
    if current.role not in {UserRole.ADMIN, UserRole.DEVELOPER}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")

    filters = []
    if user_id is not None:
        filters.append(AuditLog.user_id == user_id)
    if event_type:
        filters.append(AuditLog.event_type == event_type)
    if from_date:
        filters.append(AuditLog.timestamp >= from_date)
    if to_date:
        filters.append(AuditLog.timestamp <= to_date)

    stmt = select(AuditLog).order_by(AuditLog.timestamp.desc()).limit(500)
    if filters:
        stmt = stmt.where(and_(*filters))

    result = await db.execute(stmt)
    logs = result.scalars().all()
    return [
        AuditOut(
            id=l.id,
            user_id=l.user_id,
            query_request_id=l.query_request_id,
            event_type=l.event_type,
            details=l.details,
            ip_address=l.ip_address,
            timestamp=l.timestamp,
        )
        for l in logs
    ]
