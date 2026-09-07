"""Shared FastAPI dependencies.

``DbSession`` is the one sanctioned way to receive a database session in a
route. ``scripts/check_route_conventions.py`` (R3) rejects any other spelling.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.utils.db import get_session

DbSession = Annotated[AsyncSession, Depends(get_session)]
