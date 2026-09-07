"""Request correlation as pure ASGI middleware.

Not an ``@app.middleware("http")`` function: Starlette's 500 handler runs
outside user HTTP middleware, so an HTTP-middleware implementation unwinds
before the error response is built and the one request you most want to
correlate is the one that loses its header. Wrapping ``send`` covers every
response the app produces; logging before re-raising covers the one it does not.
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable, MutableMapping
from typing import Any

from starlette.datastructures import Headers, MutableHeaders

from app.observability.context import (
    FIELD_REQUEST_ID,
    bind,
    new_correlation_id,
    sanitize_correlation_id,
)

Scope = MutableMapping[str, Any]
Receive = Callable[[], Awaitable[MutableMapping[str, Any]]]
Send = Callable[[MutableMapping[str, Any]], Awaitable[None]]

REQUEST_ID_HEADER = "X-Request-ID"
logger = logging.getLogger(__name__)


class RequestCorrelationMiddleware:
    """Bind a request id for the request's lifetime and echo it on the response."""

    def __init__(self, app: Callable[[Scope, Receive, Send], Awaitable[None]]) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        inbound = Headers(scope=scope).get(REQUEST_ID_HEADER.lower())
        request_id = sanitize_correlation_id(inbound) or new_correlation_id()
        scope.setdefault("state", {})["request_id"] = request_id

        async def send_with_header(message: MutableMapping[str, Any]) -> None:
            if message["type"] == "http.response.start":
                MutableHeaders(scope=message)[REQUEST_ID_HEADER] = request_id
            await send(message)

        with bind(**{FIELD_REQUEST_ID: request_id}):
            try:
                await self.app(scope, receive, send_with_header)
            except Exception:
                logger.exception(
                    "unhandled error method=%s path=%s", scope.get("method"), scope.get("path")
                )
                raise
