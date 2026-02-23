"""Approval endpoints."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.security import get_current_user
from models.approval import ApprovalRequest
from models.enums import ApprovalStatus, QueryStatus, UserRole
from models.query_request import QueryRequest
from models.user import User
from schemas.approval import ApprovalDecisionIn, ApprovalOut

router = APIRouter(prefix="/approvals", tags=["approvals"])


@router.get("/pending", response_model=list[ApprovalOut])
async def list_pending(db: AsyncSession = Depends(get_db), current: User = Depends(get_current_user)) -> list[ApprovalOut]:
    if current.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")

    rows = await db.execute(select(ApprovalRequest).where(ApprovalRequest.status == ApprovalStatus.PENDING))
    approvals = rows.scalars().all()
    return [
        ApprovalOut(
            id=a.id,
            query_request_id=a.query_request_id,
            reviewer_id=a.reviewer_id,
            status=a.status.value,
            reviewer_comment=a.reviewer_comment,
            timeout_at=a.timeout_at,
            created_at=a.created_at,
            decided_at=a.decided_at,
        )
        for a in approvals
    ]


@router.post("/decision", response_model=ApprovalOut)
async def decide_approval(
    payload: ApprovalDecisionIn,
    db: AsyncSession = Depends(get_db),
    current: User = Depends(get_current_user),
) -> ApprovalOut:
    if current.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")

    row = await db.execute(select(ApprovalRequest).where(ApprovalRequest.query_request_id == payload.query_request_id))
    approval = row.scalar_one_or_none()
    if not approval:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Approval request not found")

    if approval.status != ApprovalStatus.PENDING:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Approval already decided")

    approval.reviewer_id = current.id
    approval.status = ApprovalStatus.APPROVED if payload.approve else ApprovalStatus.REJECTED
    approval.reviewer_comment = payload.comment
    approval.decided_at = datetime.now(timezone.utc)

    query = await db.execute(select(QueryRequest).where(QueryRequest.id == approval.query_request_id))
    query_request = query.scalar_one_or_none()
    if query_request:
        query_request.status = QueryStatus.APPROVED if payload.approve else QueryStatus.REJECTED

    await db.commit()

    return ApprovalOut(
        id=approval.id,
        query_request_id=approval.query_request_id,
        reviewer_id=approval.reviewer_id,
        status=approval.status.value,
        reviewer_comment=approval.reviewer_comment,
        timeout_at=approval.timeout_at,
        created_at=approval.created_at,
        decided_at=approval.decided_at,
    )
