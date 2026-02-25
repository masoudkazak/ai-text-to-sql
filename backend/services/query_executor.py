from __future__ import annotations

import re
import time
from collections.abc import Sequence
from typing import Any

from sqlalchemy import text
from sqlalchemy.exc import InterfaceError, OperationalError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings


class QueryExecutionError(Exception):
    def __init__(self, raw_error: str, *, detail: str, status_code: int) -> None:
        super().__init__(raw_error)
        self.detail = detail
        self.status_code = status_code


class QueryExecutor:
    def _apply_limit(self, sql: str) -> str:
        if sql.strip().upper().startswith("SELECT") and "LIMIT" not in sql.upper():
            return f"{sql.rstrip(';')} LIMIT {settings.MAX_RESULT_ROWS}"
        return sql

    def _sanitize_params(self, sql: str) -> tuple[str, dict[str, Any]]:
        placeholders = set(re.findall(r":([a-zA-Z_][a-zA-Z0-9_]*)", sql))
        return sql, {name: None for name in placeholders}

    async def execute(self, db: AsyncSession, sql: str) -> tuple[list[dict[str, Any]], int, int]:
        sql_limited = self._apply_limit(sql)
        sql_safe, params = self._sanitize_params(sql_limited)

        started = time.perf_counter()
        try:
            result = await db.execute(text(sql_safe), params)
            elapsed_ms = int((time.perf_counter() - started) * 1000)

            if result.returns_rows:
                mappings: Sequence[Any] = result.mappings().fetchall()
                rows = [dict(x) for x in mappings][: settings.MAX_RESULT_ROWS]
                return rows, len(rows), elapsed_ms

            await db.commit()
            return [], result.rowcount or 0, elapsed_ms
        except SQLAlchemyError as exc:
            await db.rollback()
            if isinstance(exc, (OperationalError, InterfaceError)):
                raise QueryExecutionError(
                    str(exc),
                    detail="Database is temporarily unavailable. Please try again.",
                    status_code=503,
                ) from exc

            raise QueryExecutionError(
                str(exc),
                detail="Generated SQL is not valid for the current schema. Please refine your prompt and try again.",
                status_code=422,
            ) from exc
