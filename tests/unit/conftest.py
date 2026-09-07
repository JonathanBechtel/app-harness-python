"""Unit tests never touch a database. The fixture below makes that mechanical."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine


@pytest.fixture(autouse=True)
def forbid_database(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Fail fast if a unit test tries to open a real connection."""

    def _boom(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("unit tests must not connect to a database; use tests/integration")

    monkeypatch.setattr(AsyncEngine, "connect", _boom)
    monkeypatch.setattr(AsyncEngine, "begin", _boom)
    yield
