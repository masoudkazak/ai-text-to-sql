from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select, update
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
from services.llm_service import LLMService, LLMServiceError
from services.query_executor import QueryExecutionError, QueryExecutor
from services.sql_analyzer import SQLAnalyzer

from .query_helpers import build_schema_snapshot, execute_query_request

router = APIRouter(prefix="/query", tags=["query"])

llm_service = LLMService()
sql_analyzer = SQLAnalyzer()
governance_engine = GovernanceEngine()
query_executor = QueryExecutor()
audit_service = AuditService()


@router.post("", response_model=QueryResponse)
async def process_query(
    payload: QueryInput,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> QueryResponse:
    user_id = user.id
    request_ip = request.client.host if request.client else None

    await enforce_rate_limit(user, request_ip)
    await enforce_ai_daily_limit()

    await audit_service.log(
        db, user_id, "QUERY_RECEIVED", {"text": payload.text}, ip_address=request_ip
    )

    schema, available_tables, table_columns = await build_schema_snapshot(db)
    allowed_by_admin = {t.lower() for t in user.allowed_tables}
    effective_allowed_tables = [
        t
        for t in available_tables
        if not allowed_by_admin or t.lower() in allowed_by_admin
    ]
    effective_schema = "; ".join(
        f"{table}({', '.join(table_columns.get(table, []))})"
        for table in effective_allowed_tables
    )
    try:
        generated_sql = await llm_service.text_to_sql(
            payload.text,
            schema=effective_schema or schema,
            allowed_tables=effective_allowed_tables or available_tables,
        )
    except LLMServiceError as exc:
        await audit_service.log(
            db, user_id, "LLM_ERROR", {"error": exc.detail}, None, request_ip
        )
        raise HTTPException(status_code=exc.status_code, detail=exc.detail)

    await audit_service.log(
        db, user_id, "SQL_GENERATED", {"sql": generated_sql}, ip_address=request_ip
    )

    analysis = sql_analyzer.analyze(generated_sql)
    governance: GovernanceDecision = governance_engine.decide(user, analysis)

    if (
        user.role == UserRole.VIEWER
        and analysis.query_type == "SELECT"
        and "LIMIT" not in generated_sql.upper()
    ):
        generated_sql = generated_sql.rstrip(";") + " LIMIT 100"

    query_request = QueryRequest(
        user_id=user_id,
        original_text=payload.text,
        generated_sql=generated_sql,
        sql_analysis=analysis.model_dump(),
        governance_decision=GovernanceDecisionType(governance.decision),
        governance_reason=governance.reason,
        status=QueryStatus.PENDING,
    )
    db.add(query_request)
    await db.commit()
    query_request_id = query_request.id

    if governance.decision == "DENIED":
        query_request.status = QueryStatus.REJECTED
        await db.commit()
        await audit_service.log(
            db,
            user_id,
            "DENIED",
            {"reason": governance.reason},
            query_request_id,
            request_ip,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=governance.reason
        )

    if governance.decision == "REQUIRES_APPROVAL":
        approval = ApprovalRequest(
            query_request_id=query_request_id, status=ApprovalStatus.PENDING
        )
        db.add(approval)
        await db.commit()
        await audit_service.log(
            db,
            user_id,
            "APPROVAL_REQUIRED",
            {"reason": governance.reason},
            query_request_id,
            request_ip,
        )

        return QueryResponse(
            query_request_id=query_request_id,
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
            governance_mask_columns=governance.mask_columns,
            user_id=user_id,
            request_ip=request_ip,
            query_executor=query_executor,
            audit_service=audit_service,
        )

        return QueryResponse(
            query_request_id=query_request_id,
            generated_sql=generated_sql,
            sql_analysis=analysis,
            governance=governance,
            status=QueryStatus.EXECUTED.value,
            result=rows,
            created_at=query_request.created_at,
        )
    except QueryExecutionError as exc:
        await db.execute(
            update(QueryRequest)
            .where(QueryRequest.id == query_request_id)
            .values(status=QueryStatus.FAILED)
        )
        await db.commit()
        await audit_service.log(
            db, user_id, "FAILED", {"error": str(exc)}, query_request_id, request_ip
        )
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.get("/{query_request_id}", response_model=QueryResponse)
async def get_query_request_result(
    query_request_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> QueryResponse:
    user_id = user.id
    request_ip = request.client.host if request.client else None

    row = await db.execute(
        select(QueryRequest).where(QueryRequest.id == query_request_id)
    )
    query_request = row.scalar_one_or_none()
    if not query_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Query request not found"
        )

    if query_request.user_id != user.id and user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not allowed to access this query",
        )

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
                governance_mask_columns=governance.mask_columns,
                user_id=user_id,
                request_ip=request_ip,
                query_executor=query_executor,
                audit_service=audit_service,
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
            query_request_id_saved = query_request.id
            await db.execute(
                update(QueryRequest)
                .where(QueryRequest.id == query_request_id_saved)
                .values(status=QueryStatus.FAILED)
            )
            await db.commit()
            await audit_service.log(
                db,
                user_id,
                "FAILED",
                {"error": str(exc), "query_request_id": query_request_id_saved},
                query_request_id_saved,
                request_ip,
            )
            raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

    return QueryResponse(
        query_request_id=query_request.id,
        generated_sql=query_request.generated_sql,
        sql_analysis=analysis,
        governance=governance,
        status=query_request.status.value,
        result=None,
        created_at=query_request.created_at,
    )
