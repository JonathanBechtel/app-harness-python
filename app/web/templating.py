"""Shared Jinja configuration.

Registering filters in one place keeps the app's template environment and any
standalone environment (tests rendering a partial directly) in agreement.
"""

from __future__ import annotations

from datetime import datetime

from jinja2 import Environment


def _isoformat(value: datetime | None) -> str:
    return value.isoformat(timespec="seconds") if value else ""


def register_template_filters(env: Environment) -> None:
    """Register the app's custom Jinja filters on ``env``."""
    env.filters["iso"] = _isoformat
