"""Shared scaffolding for ``app/cli`` entrypoints."""

from __future__ import annotations

import asyncio
import sys
from collections.abc import Awaitable, Callable

from app.logging_config import setup_logging
from app.observability import bind_job_run
from app.utils.db import dispose_engine


def run_job(name: str, main: Callable[[], Awaitable[int]]) -> None:
    """Run an async job entrypoint with logging, correlation, and a clean exit code."""
    setup_logging()

    async def _run() -> int:
        try:
            with bind_job_run(name):
                return await main()
        finally:
            await dispose_engine()

    sys.exit(asyncio.run(_run()))
