"""The eval harness runs end to end with the credential-free responder."""

from __future__ import annotations

import asyncio

import pytest

from evals.runner import default_responder, run_suite


def test_core_suite_runs_and_scores() -> None:
    """The example suite completes, reports per-dataset accuracy/consistency, and passes its gates."""
    report = asyncio.run(run_suite("core", 2, default_responder))
    assert report["passed"] is True
    assert report["datasets"][0]["accuracy"] == pytest.approx(1.0)
