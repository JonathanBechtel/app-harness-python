"""Log formatters: JSON for deployed output, console for local reading."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any

from app.observability.context import current_context
from app.observability.scrubbing import scrub

_STANDARD_ATTRS = set(logging.LogRecord("", 0, "", 0, "", (), None).__dict__) | {
    "message",
    "asctime",
}


class _ScrubbingFormatter(logging.Formatter):
    def __init__(self, *args: Any, secrets: tuple[str, ...] = (), **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._secrets = secrets

    def _extras(self, record: logging.LogRecord) -> dict[str, Any]:
        extras = {k: v for k, v in record.__dict__.items() if k not in _STANDARD_ATTRS}
        extras.update(current_context())
        return extras


class ConsoleFormatter(_ScrubbingFormatter):
    """Human-readable line with bound context appended as key=value pairs."""

    def format(self, record: logging.LogRecord) -> str:
        base = super().format(record)
        extras = self._extras(record)
        if extras:
            base += " " + " ".join(f"{k}={v}" for k, v in extras.items())
        return scrub(base, self._secrets)


class JsonFormatter(_ScrubbingFormatter):
    """One JSON object per line."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        payload.update(self._extras(record))
        return scrub(json.dumps(payload, default=str), self._secrets)
