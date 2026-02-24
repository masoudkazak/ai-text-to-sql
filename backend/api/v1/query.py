from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.security import get_current_user
from middleware.rate_limiter import enforce_ai_daily_limit, enforce_rate_limit
from models.approval import ApprovalRequest
from models.enums import ApprovalStatus, GovernanceDecisionType, QueryStatus, UserRole
from models.query_request import QueryRequest
from models.user import User
from schemas.query import GovernanceDecision, QueryInput, QueryResponse
from services.audit_service import AuditService
from services.governance_engine import GovernanceEngine
from services.llm_service import LLMService
from services.query_executor import QueryExecutionError, QueryExecutor
from services.sql_analyzer import SQLAnalyzer

router = APIRouter(prefix="/query", tags=["query"])

llm_service = LLMService()
sql_analyzer = SQLAnalyzer()
governance_engine = GovernanceEngine()
query_executor = QueryExecutor()
audit_service = AuditService()


def mask_value(column: str, value: object) -> object:
    if value is None or not isinstance(value, str):
        return value

    c = column.lower()
    if c == "phone" and len(value) >= 7:
        return f"{value[:3]}****{value[-3:]}"
    if c == "email" and "@" in value:
        user, _, domain = value.partition("@")
        return f"{user[:2]}**@***.{domain.split('.')[-1]}"
    if c == "credit_card" and len(value) >= 4:
        return f"************{value[-4:]}"
    if c in {"password", "national_id"}:
        return "***MASKED***"
    return value


def apply_mask(rows: list[dict], columns: list[str]) -> list[dict]:
    cols = {c.lower() for c in columns}
    if not cols:
        return rows

    masked: list[dict] = []
    for row in rows:
        masked.append({k: mask_value(k, v) if k.lower() in cols else v for k, v in row.items()})
    return masked


async def build_schema_snapshot(_: AsyncSession) -> str:
    return "users(id,email,role), query_requests(...), approval_requests(...), audit_logs(...), travel_planner(org,dest,days,date,query,level,reference_information)"


async def execute_query_request(
    db: AsyncSession,
    query_request: QueryRequest,
    governance: GovernanceDecision,
    user_id: int,
    request_ip: str | None,
) -> list[dict[str, Any]]:
    rows, row_count, elapsed_ms = await query_executor.execute(db, query_request.generated_sql)
    rows = apply_mask(rows, governance.mask_columns)

    query_request.status = QueryStatus.EXECUTED
    query_request.result_row_count = row_count
    query_request.execution_time_ms = elapsed_ms
    query_request.executed_at = datetime.now(timezone.utc)
    await db.commit()

    await audit_service.log(
        db,
        user_id,
        "EXECUTED",
        {"row_count": row_count, "execution_time_ms": elapsed_ms, "query_request_id": query_request.id},
        query_request.id,
        request_ip,
    )
    return rows


@router.post("", response_model=QueryResponse)
async def process_query(
    payload: QueryInput,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> QueryResponse:
    await enforce_rate_limit(user)
    await enforce_ai_daily_limit()

    await audit_service.log(db, user.id, "QUERY_RECEIVED", {"text": payload.text}, ip_address=request.client.host if request.client else None)

    schema = await build_schema_snapshot(db)
    generated_sql = await llm_service.text_to_sql(payload.text, schema=schema, allowed_tables=user.allowed_tables)

    await audit_service.log(db, user.id, "SQL_GENERATED", {"sql": generated_sql}, ip_address=request.client.host if request.client else None)

    analysis = sql_analyzer.analyze(generated_sql)
    governance: GovernanceDecision = governance_engine.decide(user, analysis)

    if user.role == UserRole.VIEWER and analysis.query_type == "SELECT" and "LIMIT" not in generated_sql.upper():
        generated_sql = generated_sql.rstrip(";") + " LIMIT 100"

    query_request = QueryRequest(
        user_id=user.id,
        original_text=payload.text,
        generated_sql=generated_sql,
        sql_analysis=analysis.model_dump(),
        governance_decision=GovernanceDecisionType(governance.decision),
        governance_reason=governance.reason,
        status=QueryStatus.PENDING,
    )
    db.add(query_request)
    await db.commit()
    await db.refresh(query_request)

    if governance.decision == "DENIED":
        query_request.status = QueryStatus.REJECTED
        await db.commit()
        await audit_service.log(db, user.id, "DENIED", {"reason": governance.reason}, query_request.id, request.client.host if request.client else None)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=governance.reason)

    if governance.decision == "REQUIRES_APPROVAL":
        approval = ApprovalRequest(query_request_id=query_request.id, status=ApprovalStatus.PENDING)
        db.add(approval)
        await db.commit()
        await audit_service.log(db, user.id, "APPROVAL_REQUIRED", {"reason": governance.reason}, query_request.id, request.client.host if request.client else None)

        return QueryResponse(
            query_request_id=query_request.id,
            generated_sql=generated_sql,
            sql_analysis=analysis,
            governance=governance,
            status=QueryStatus.PENDING.value,
            result=None,
            created_at=query_request.created_at,
        )

    try:
        rows = await execute_query_request(
            db=db,
            query_request=query_request,
            governance=governance,
            user_id=user.id,
            request_ip=request.client.host if request.client else None,
        )

        return QueryResponse(
            query_request_id=query_request.id,
            generated_sql=generated_sql,
            sql_analysis=analysis,
            governance=governance,
            status=QueryStatus.EXECUTED.value,
            result=rows,
            created_at=query_request.created_at,
        )
    except QueryExecutionError as exc:
        query_request.status = QueryStatus.FAILED
        await db.commit()
        await audit_service.log(db, user.id, "FAILED", {"error": str(exc)}, query_request.id, request.client.host if request.client else None)
        raise HTTPException(status_code=500, detail=f"Execution failed: {exc}") from exc


@router.get("/{query_request_id}", response_model=QueryResponse)
async def get_query_request_result(
    query_request_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> QueryResponse:
    row = await db.execute(select(QueryRequest).where(QueryRequest.id == query_request_id))
    query_request = row.scalar_one_or_none()
    if not query_request:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Query request not found")

    if query_request.user_id != user.id and user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to access this query")

    analysis = sql_analyzer.analyze(query_request.generated_sql)
    governance = GovernanceDecision(
        decision=query_request.governance_decision.value,
        reason=query_request.governance_reason,
        risk_level=analysis.risk_level,
        mask_columns=analysis.sensitive_columns_found,
    )

    if query_request.status == QueryStatus.APPROVED:
        try:
            rows = await execute_query_request(
                db=db,
                query_request=query_request,
                governance=governance,
                user_id=user.id,
                request_ip=request.client.host if request.client else None,
            )
            return QueryResponse(
                query_request_id=query_request.id,
                generated_sql=query_request.generated_sql,
                sql_analysis=analysis,
                governance=governance,
                status=query_request.status.value,
                result=rows,
                created_at=query_request.created_at,
            )
        except QueryExecutionError as exc:
            query_request.status = QueryStatus.FAILED
            await db.commit()
            await audit_service.log(
                db,
                user.id,
                "FAILED",
                {"error": str(exc), "query_request_id": query_request.id},
                query_request.id,
                request.client.host if request.client else None,
            )
            raise HTTPException(status_code=500, detail=f"Execution failed: {exc}") from exc

    return QueryResponse(
        query_request_id=query_request.id,
        generated_sql=query_request.generated_sql,
        sql_analysis=analysis,
        governance=governance,
        status=query_request.status.value,
        result=None,
        created_at=query_request.created_at,
    )
