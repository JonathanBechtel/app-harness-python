"""Runtime guard against network I/O inside an open database transaction.

Failure this descends from: an external HTTP call four frames deep inside a
``db.begin()`` block held a transaction (and the locks under it) across a
network round-trip. AST checkers cannot see across frames; this guard can.

Behaviour is asymmetric by design: every environment except ``prod`` raises
``NetworkIOGuardViolation`` so the bug surfaces locally, in tests, and in
staging; prod logs a warning with the stack so a latent path is visible without
breaking the request.

Wire it into every outbound HTTP client::

    httpx.AsyncClient(event_hooks={"request": [guard_httpx_request]})
"""

from __future__ import annotations

import logging
import traceback
from contextvars import ContextVar
from typing import Any

from sqlalchemy import event
from sqlalchemy.orm import Session, SessionTransaction

from app.config import settings

logger = logging.getLogger(__name__)

_active_transactions: ContextVar[frozenset[int]] = ContextVar(
    "active_db_transactions", default=frozenset()
)


class NetworkIOGuardViolation(RuntimeError):
    """Raised outside production when network I/O starts inside a transaction."""


@event.listens_for(Session, "after_begin")
def _track_begin(session: Session, transaction: SessionTransaction, connection: Any) -> None:
    _active_transactions.set(_active_transactions.get() | {id(transaction)})


@event.listens_for(Session, "after_transaction_end")
def _track_end(session: Session, transaction: SessionTransaction) -> None:
    _active_transactions.set(_active_transactions.get() - {id(transaction)})


def transaction_depth() -> int:
    """Number of open transactions on the current task."""
    return len(_active_transactions.get())


def guard_network_io(description: str) -> None:
    """Call before issuing any network request; raises or warns if a transaction is open."""
    if transaction_depth() == 0:
        return
    message = f"network I/O ({description}) attempted inside an open database transaction"
    if settings.is_prod:
        logger.warning("%s\n%s", message, "".join(traceback.format_stack(limit=12)))
        return
    raise NetworkIOGuardViolation(message)


async def guard_httpx_request(request: Any) -> None:
    """Httpx ``request`` event hook."""
    guard_network_io(f"{request.method} {request.url}")
