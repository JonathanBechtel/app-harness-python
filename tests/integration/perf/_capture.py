"""Count SQL statements issued through an engine during a block."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncEngine


@contextmanager
def count_statements(engine: AsyncEngine) -> Iterator[list[str]]:
    """Yield a list that fills with every statement executed on ``engine``."""
    statements: list[str] = []

    def _record(conn: Any, cursor: Any, statement: str, *_: Any) -> None:
        if not statement.lstrip().upper().startswith(("SET ", "SHOW ")):
            statements.append(statement)

    event.listen(engine.sync_engine, "before_cursor_execute", _record)
    try:
        yield statements
    finally:
        event.remove(engine.sync_engine, "before_cursor_execute", _record)
