"""Smoke: the landing page renders and its JS ran."""

from __future__ import annotations

import pytest

from tests.e2e.conftest import SCREENSHOTS


@pytest.mark.e2e
def test_landing_page_renders_and_js_runs(page, base_url: str) -> None:
    """The page loads, the landing card is visible, main.js marked the document ready, and a screenshot is saved."""
    page.goto(base_url + "/")
    page.wait_for_load_state("networkidle")
    assert page.locator('[data-testid="landing"]').is_visible()
    assert page.evaluate("document.documentElement.dataset.jsReady") == "true"
    page.screenshot(path=str(SCREENSHOTS / "landing.png"), full_page=True)
