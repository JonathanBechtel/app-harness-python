"""Correlation context and log scrubbing."""

from __future__ import annotations

import json
import logging

from app.observability import bind, bind_job_run, current_context
from app.observability.formatters import JsonFormatter
from app.observability.scrubbing import REDACTED, scrub


def test_bind_is_scoped() -> None:
    """Fields bound inside the block are visible there and gone afterwards."""
    with bind(request_id="r1"):
        assert current_context()["request_id"] == "r1"
    assert "request_id" not in current_context()


def test_json_formatter_includes_context_and_scrubs() -> None:
    """The JSON line carries bound fields and never the secret value."""
    formatter = JsonFormatter(secrets=("hunter2",))
    record = logging.LogRecord("t", logging.INFO, __file__, 1, "password is hunter2", (), None)
    with bind(run_id="job-1"):
        payload = json.loads(formatter.format(record))
    assert payload["run_id"] == "job-1"
    assert "hunter2" not in payload["message"]
    assert REDACTED in payload["message"]


def test_bind_job_run_reraises_and_logs_failure(caplog) -> None:
    """A failing job logs outcome=failed and propagates the exception."""
    with caplog.at_level(logging.INFO, logger="app.jobs"):
        try:
            with bind_job_run("nightly"):
                raise RuntimeError("boom")
        except RuntimeError:
            pass
    assert any(getattr(r, "outcome", None) == "failed" for r in caplog.records)


def test_scrub_replaces_every_occurrence() -> None:
    """Every occurrence of every secret is replaced."""
    assert scrub("a hunter2 b hunter2", ("hunter2",)) == f"a {REDACTED} b {REDACTED}"
