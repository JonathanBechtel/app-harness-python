"""Browser tests against a RUNNING server (make dev), opt-in via `-m e2e`.

Screenshots land in tests/e2e/screenshots/ for a human (or a multimodal agent)
to read. There is no pixel diffing: the verdict is a judgment, not a hash.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path

import pytest

SCREENSHOTS = Path(__file__).parent / "screenshots"


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Skip e2e tests unless explicitly selected with -m e2e."""
    if config.getoption("-m") and "e2e" in str(config.getoption("-m")):
        return
    skip = pytest.mark.skip(reason="e2e tests run only with `-m e2e` against a live server")
    for item in items:
        if "e2e" in item.keywords:
            item.add_marker(skip)


@pytest.fixture(scope="session")
def base_url() -> str:
    """Server under test."""
    return os.environ.get("TEST_BASE_URL", "http://localhost:8000")


@pytest.fixture()
def page(base_url: str) -> Iterator[object]:
    """A Playwright page at a phone-ish and desktop-capable viewport."""
    playwright = pytest.importorskip("playwright.sync_api")
    SCREENSHOTS.mkdir(exist_ok=True)
    with playwright.sync_playwright() as p:
        browser = p.chromium.launch(headless=os.environ.get("PLAYWRIGHT_HEADLESS", "1") == "1")
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        page.base_url = base_url  # type: ignore[attr-defined]
        yield page
        browser.close()
