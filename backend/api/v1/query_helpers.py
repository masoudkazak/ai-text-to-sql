from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from models.enums import QueryStatus
from models.query_request import QueryRequest
from services.audit_service import AuditService
from services.query_executor import QueryExecutor
from services.table_service import list_non_blacklisted_tables


def mask_value(column: str, value: object) -> object:
    if value is None or not isinstance(value, str):
        return value

    c = column.lower()
    if "password" in c:
        return "***MASKED***"
    if c == "phone" and len(value) >= 7:
        return f"{value[:3]}****{value[-3:]}"
    if c == "email" and "@" in value:
        user, _, domain = value.partition("@")
        return f"{user[:2]}**@***.{domain.split('.')[-1]}"
    if c == "credit_card" and len(value) >= 4:
        return f"************{value[-4:]}"
    if c == "national_id":
        return "***MASKED***"
    return value


def apply_mask(rows: list[dict], columns: list[str]) -> list[dict]:
    cols = {c.lower() for c in columns}
    if not cols:
        cols = set()

    masked: list[dict] = []
    for row in rows:
        masked.append({k: mask_value(k, v) if (k.lower() in cols or "password" in k.lower()) else v for k, v in row.items()})
    return masked


async def build_schema_snapshot(db: AsyncSession) -> tuple[str, list[str], dict[str, list[str]]]:
    from sqlalchemy import select, text
    
    available_tables = await list_non_blacklisted_tables(db)
    if not available_tables:
        return "", [], {}

    result = await db.execute(
        text(
            """
            SELECT table_name, column_name
            FROM information_schema.columns
            WHERE table_schema = 'public'
            ORDER BY table_name, ordinal_position
            """
        )
    )
    table_columns: dict[str, list[str]] = {table: [] for table in available_tables}
    for row in result.mappings():
        table_name = row["table_name"]
        column_name = row["column_name"]
        if table_name in table_columns and column_name:
            table_columns[table_name].append(column_name)

    schema = "; ".join(f"{table}({', '.join(columns)})" for table, columns in table_columns.items())
    return schema, available_tables, table_columns


async def execute_query_request(
    db: AsyncSession,
    query_request: QueryRequest,
    governance_mask_columns: list[str],
    user_id: int,
    request_ip: str | None,
    query_executor: QueryExecutor,
    audit_service: AuditService,
) -> list[dict[str, Any]]:
    rows, row_count, elapsed_ms = await query_executor.execute(db, query_request.generated_sql)
    rows = apply_mask(rows, governance_mask_columns)

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
