from __future__ import annotations

import re
import time
import uuid

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from structlog.contextvars import bind_contextvars, clear_contextvars

CORRELATION_ID_PATTERN = re.compile(r"req-[0-9a-fA-F]{8}")


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Each request starts with a clean context so concurrent or reused worker
        # tasks cannot inherit metadata from an earlier request.
        clear_contextvars()

        supplied_id = request.headers.get("x-request-id", "").strip()
        correlation_id = (
            supplied_id
            if CORRELATION_ID_PATTERN.fullmatch(supplied_id)
            else f"req-{uuid.uuid4().hex[:8]}"
        )
        bind_contextvars(correlation_id=correlation_id)
        request.state.correlation_id = correlation_id

        start = time.perf_counter()
        try:
            response = await call_next(request)
            elapsed_ms = int((time.perf_counter() - start) * 1000)
            response.headers["x-request-id"] = correlation_id
            response.headers["x-response-time-ms"] = str(elapsed_ms)
            return response
        finally:
            clear_contextvars()
