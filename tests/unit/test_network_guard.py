"""Runtime guard: network I/O inside a transaction raises outside prod."""

from __future__ import annotations

import pytest

from app.utils import network_guard


def test_guard_passes_with_no_transaction() -> None:
    """No open transaction means the guard is a no-op."""
    network_guard.guard_network_io("GET x")


def test_guard_raises_inside_transaction(monkeypatch: pytest.MonkeyPatch) -> None:
    """Simulated open transaction + non-prod env raises NetworkIOGuardViolation."""
    token = network_guard._active_transactions.set(frozenset({1}))
    try:
        with pytest.raises(network_guard.NetworkIOGuardViolation):
            network_guard.guard_network_io("GET x")
    finally:
        network_guard._active_transactions.reset(token)


def test_guard_warns_in_prod(monkeypatch: pytest.MonkeyPatch, caplog) -> None:
    """In prod the guard logs a warning with the stack instead of raising."""
    monkeypatch.setattr(network_guard.settings, "env", "prod")
    token = network_guard._active_transactions.set(frozenset({1}))
    try:
        network_guard.guard_network_io("GET x")
    finally:
        network_guard._active_transactions.reset(token)
    assert any("inside an open database transaction" in r.message for r in caplog.records)
