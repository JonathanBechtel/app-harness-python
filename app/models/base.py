"""Shared table mixins."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlmodel import Field


def utcnow() -> datetime:
    """Timezone-aware UTC now (SQLModel default factory)."""
    return datetime.now(UTC)


class TimestampMixin:
    """``created_at`` / ``updated_at`` columns, set by the application."""

    created_at: datetime = Field(default_factory=utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=utcnow, nullable=False)
