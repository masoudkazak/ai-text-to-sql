from datetime import datetime, timezone
import asyncio
import time
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from models.enums import QueryStatus
from models.query_request import QueryRequest
from services.audit_service import AuditService
from services.query_executor import QueryExecutor

_SCHEMA_CACHE_TTL_SECONDS = 600.0
_schema_cache_lock = asyncio.Lock()
_schema_cache: dict[str, Any] = {
    "expires_at": 0.0,
    "schema": "",
    "tables": [],
    "table_columns": {},
}


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
    now = time.monotonic()
    if _schema_cache["expires_at"] > now:
        return _schema_cache["schema"], list(_schema_cache["tables"]), dict(_schema_cache["table_columns"])

    async with _schema_cache_lock:
        now = time.monotonic()
        if _schema_cache["expires_at"] > now:
            return _schema_cache["schema"], list(_schema_cache["tables"]), dict(_schema_cache["table_columns"])

        result = await db.execute(
            text(
                """
                SELECT t.table_name, c.column_name
                FROM information_schema.tables AS t
                LEFT JOIN information_schema.columns AS c
                    ON c.table_schema = t.table_schema
                   AND c.table_name = t.table_name
                WHERE t.table_schema = 'public'
                  AND t.table_type = 'BASE TABLE'
                ORDER BY t.table_name, c.ordinal_position
                """
            )
        )
        blacklisted = {t.lower() for t in settings.BLACKLISTED_TABLES}
        table_columns: dict[str, list[str]] = {}

        for row in result.mappings():
            table_name = row["table_name"]
            if not table_name or table_name.lower() in blacklisted:
                continue

            if table_name not in table_columns:
                table_columns[table_name] = []

            column_name = row["column_name"]
            if column_name:
                table_columns[table_name].append(column_name)

        available_tables = sorted(table_columns.keys())
        schema = "; ".join(f"{table}({', '.join(table_columns[table])})" for table in available_tables)

        _schema_cache["schema"] = schema
        _schema_cache["tables"] = available_tables
        _schema_cache["table_columns"] = table_columns
        _schema_cache["expires_at"] = now + _SCHEMA_CACHE_TTL_SECONDS

        return schema, list(available_tables), dict(table_columns)


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
