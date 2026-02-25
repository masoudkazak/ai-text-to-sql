import logging
import time
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from typing import Any
from uuid import uuid4

from sqlalchemy import Engine, event
from sqlalchemy.ext.asyncio import AsyncEngine
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.types import ASGIApp


@dataclass
class QueryExecution:
    sql: str
    params: str
    duration_ms: float


@dataclass
class RequestSqlStats:
    total_queries: int = 0
    total_sql_time_ms: float = 0.0
    queries: list[QueryExecution] = field(default_factory=list)


_request_sql_context: ContextVar[RequestSqlStats | None] = ContextVar("request_sql_context", default=None)
_sql_logger_name = "sql_monitor"
_listeners_registered = False


def setup_sql_monitor_logger(log_path: str | Path | None = None) -> logging.Logger:
    logger = logging.getLogger(_sql_logger_name)
    logger.setLevel(logging.INFO)
    logger.propagate = False

    if logger.handlers:
        return logger

    if log_path is None:
        log_path = Path(__file__).resolve().parent.parent / "logs" / "sql-monitor.log"
    else:
        log_path = Path(log_path)

    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        handler = TimedRotatingFileHandler(
            filename=str(log_path),
            when="midnight",
            interval=1,
            backupCount=30,
            encoding="utf-8",
        )
    except OSError:
        fallback = Path("/tmp/sql-monitor.log")
        fallback.parent.mkdir(parents=True, exist_ok=True)
        handler = TimedRotatingFileHandler(
            filename=str(fallback),
            when="midnight",
            interval=1,
            backupCount=30,
            encoding="utf-8",
        )
        logger.warning("sql_monitor log path is not writable, fallback path is %s", fallback)
    formatter = logging.Formatter("%(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger


def register_sql_query_listeners(engine: Engine | AsyncEngine) -> None:
    global _listeners_registered
    if _listeners_registered:
        return

    if isinstance(engine, AsyncEngine):
        engine = engine.sync_engine

    def before_cursor_execute(
        conn: Any,
        cursor: Any,
        statement: str,
        parameters: Any,
        context: Any,
        executemany: bool,
    ) -> None:
        if context is not None:
            context.query_start_time = time.perf_counter()

    def after_cursor_execute(
        conn: Any,
        cursor: Any,
        statement: str,
        parameters: Any,
        context: Any,
        executemany: bool,
    ) -> None:
        if context is None:
            return

        start = getattr(context, "query_start_time", None)
        if start is None:
            return

        stats = _request_sql_context.get()
        if stats is None:
            return

        duration_ms = (time.perf_counter() - start) * 1000
        sql_text = " ".join(statement.split())
        stats.total_queries += 1
        stats.total_sql_time_ms += duration_ms
        stats.queries.append(
            QueryExecution(sql=sql_text, params=repr(parameters), duration_ms=duration_ms)
        )

    event.listen(engine, "before_cursor_execute", before_cursor_execute)
    event.listen(engine, "after_cursor_execute", after_cursor_execute)
    _listeners_registered = True


class SQLRequestMonitorMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, logger_name: str = _sql_logger_name):
        super().__init__(app)
        self.logger = logging.getLogger(logger_name)

    async def dispatch(self, request: Request, call_next):
        request_start = time.perf_counter()
        context_token = _request_sql_context.set(RequestSqlStats())
        request_id = uuid4().hex[:8]
        status_code = 500

        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        finally:
            elapsed_ms = (time.perf_counter() - request_start) * 1000
            stats = _request_sql_context.get()
            _request_sql_context.reset(context_token)

            if stats is None:
                return

            payload = {
                "event": "api_sql_request",
                "request_id": request_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "method": request.method,
                "path": request.url.path,
                "status": status_code,
                "request_ms": round(elapsed_ms, 3),
                "total_queries": stats.total_queries,
                "total_sql_ms": round(stats.total_sql_time_ms, 3),
                "queries": [
                    {
                        "index": index,
                        "duration_ms": round(query.duration_ms, 3),
                        "sql": query.sql,
                        "params": query.params,
                    }
                    for index, query in enumerate(stats.queries, start=1)
                ],
            }
            pretty_payload = json.dumps(payload, ensure_ascii=False, indent=2)
            self.logger.info(pretty_payload + "\n")
