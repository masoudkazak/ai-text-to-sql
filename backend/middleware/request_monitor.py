import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.types import ASGIApp


class RequestMonitorMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, slow_threshold_seconds: float = 1.0) -> None:
        super().__init__(app)
        self.logger = logging.getLogger("request_monitor")
        self.slow_threshold_seconds = slow_threshold_seconds

    async def dispatch(self, request: Request, call_next):
        started = time.perf_counter()
        url = str(request.url.path)
        status_code = 500

        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        finally:
            duration = time.perf_counter() - started

            if duration > self.slow_threshold_seconds:
                self.logger.warning("SLOW REQUEST: %s took %.3fs", url, duration)

            if status_code >= 500:
                self.logger.error("ERROR %s -> %s", status_code, url)
