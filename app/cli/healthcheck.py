"""Example runtime job: probe the database and exit non-zero if it is unreachable.

Usage: ``python -m app.cli.healthcheck``. Keep it as the smallest working
example of the ``app/cli`` shape; real jobs follow the same pattern.
"""

from __future__ import annotations

import logging

from app.cli._runner import run_job
from app.utils.db import check_database_readiness

logger = logging.getLogger(__name__)


async def main() -> int:
    """Return 0 when the database answers, 1 otherwise."""
    report = await check_database_readiness()
    if report.database_ok:
        logger.info("database ok latency_ms=%s", report.latency_ms)
        return 0
    logger.error("database unavailable: %s", report.error)
    return 1


if __name__ == "__main__":
    run_job("healthcheck", main)
