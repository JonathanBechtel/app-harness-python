"""Ops plane: correlation context, log formatting, secret scrubbing.

Holds no business logic and imports nothing from the rest of the app
(import-linter contract 5). Field names are a stable vocabulary so one query
spans web requests and scheduled jobs.
"""

from app.observability.context import (
    FIELD_JOB,
    FIELD_OUTCOME,
    FIELD_REQUEST_ID,
    FIELD_RUN_ID,
    bind,
    bind_job_run,
    current_context,
    new_correlation_id,
)

__all__ = [
    "FIELD_JOB",
    "FIELD_OUTCOME",
    "FIELD_REQUEST_ID",
    "FIELD_RUN_ID",
    "bind",
    "bind_job_run",
    "current_context",
    "new_correlation_id",
]
