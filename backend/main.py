from contextlib import asynccontextmanager
import logging
import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.v1 import approvals, audit, auth, query, users
from core.config import settings
from core.database import engine
from core.redis_client import init_redis, close_redis
from core.sqlalchemy_monitor_actions import (
    SQLRequestMonitorMiddleware,
    register_sql_query_listeners,
    setup_sql_monitor_logger,
)
from middleware.request_monitor import RequestMonitorMiddleware
from scripts.seed_data import seed_if_needed

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
    force=True,
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    await init_redis()
    await seed_if_needed()
    yield
    await close_redis()


app = FastAPI(
    title=settings.APP_NAME,
    lifespan=lifespan,
    debug=settings.DEBUG,
    docs_url="/docs" if settings.ENABLE_DOCS else None,
    redoc_url="/redoc" if settings.ENABLE_DOCS else None,
    openapi_url="/openapi.json" if settings.ENABLE_DOCS else None,
)

if settings.ENVIRONMENT.lower() == "development":
    setup_sql_monitor_logger()
    register_sql_query_listeners(engine)
    app.add_middleware(SQLRequestMonitorMiddleware)

app.add_middleware(
    RequestMonitorMiddleware,
    slow_threshold_seconds=settings.REQUEST_SLOW_THRESHOLD_SECONDS,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix=settings.API_V1_PREFIX)
app.include_router(query.router, prefix=settings.API_V1_PREFIX)
app.include_router(approvals.router, prefix=settings.API_V1_PREFIX)
app.include_router(audit.router, prefix=settings.API_V1_PREFIX)
app.include_router(users.router, prefix=settings.API_V1_PREFIX)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
