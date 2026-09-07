"""Correlation context: the identity of the request or job run producing a log line.

Two questions must always be answerable: "show me every log line from the
request that 500'd" and "show me every log line from last night's failed job".
Both need an identifier bound once at the edge and carried through every
``await`` underneath it, which is what ``contextvars`` provides.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from contextvars import ContextVar
from time import perf_counter
from types import MappingProxyType
from typing import Any
from uuid import uuid4

FIELD_REQUEST_ID = "request_id"
FIELD_RUN_ID = "run_id"
FIELD_JOB = "job"
FIELD_OUTCOME = "outcome"
FIELD_DURATION_MS = "duration_ms"
OUTCOME_SUCCEEDED = "succeeded"
OUTCOME_FAILED = "failed"

# Inbound correlation IDs come from outside (a proxy, a client retry) and end up
# in log output, so they are constrained rather than trusted.
_CORRELATION_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,64}$")
_EMPTY: Mapping[str, Any] = MappingProxyType({})
_context: ContextVar[Mapping[str, Any]] = ContextVar("observability_context", default=_EMPTY)


def new_correlation_id() -> str:
    """Return a fresh correlation id."""
    return uuid4().hex


def sanitize_correlation_id(value: str | None) -> str | None:
    """Return ``value`` if it is a safe correlation id, else ``None``."""
    if value and _CORRELATION_ID_PATTERN.match(value):
        return value
    return None


def current_context() -> Mapping[str, Any]:
    """Return the fields bound for the current task (read-only)."""
    return _context.get()


@contextmanager
def bind(**fields: Any) -> Iterator[None]:
    """Bind ``fields`` onto the current context for the duration of the block."""
    merged = dict(_context.get())
    merged.update({k: v for k, v in fields.items() if v is not None})
    token = _context.set(MappingProxyType(merged))
    try:
        yield
    finally:
        _context.reset(token)


@contextmanager
def bind_job_run(job: str, run_id: str | None = None) -> Iterator[str]:
    """Bind a job run, log its outcome and duration, and re-raise failures."""
    run_id = run_id or new_correlation_id()
    log = logging.getLogger("app.jobs")
    started = perf_counter()
    with bind(**{FIELD_JOB: job, FIELD_RUN_ID: run_id}):
        try:
            yield run_id
        except Exception:
            log.exception(
                "job failed",
                extra={FIELD_OUTCOME: OUTCOME_FAILED, FIELD_DURATION_MS: _ms(started)},
            )
            raise
        log.info(
            "job succeeded",
            extra={FIELD_OUTCOME: OUTCOME_SUCCEEDED, FIELD_DURATION_MS: _ms(started)},
        )


def _ms(started: float) -> int:
    return int((perf_counter() - started) * 1000)
