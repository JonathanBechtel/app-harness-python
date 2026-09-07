"""The route table is the app's public surface; changes to it must be deliberate."""

from __future__ import annotations

from collections.abc import Iterator

from app.main import app

EXPECTED = {
    ("GET", "/health"),
    ("GET", "/health/db"),
    ("GET", "/"),
}


def _walk(routes: list[object]) -> Iterator[tuple[str, str]]:
    """Yield (method, path) for every endpoint, descending into included routers."""
    for route in routes:
        # FastAPI >= 0.141 wraps included routers; older versions inline their routes.
        inner = getattr(route, "original_router", None)
        nested = getattr(route, "routes", None) or getattr(inner, "routes", None)
        if nested and not hasattr(route, "methods"):
            yield from _walk(nested)
            continue
        methods = getattr(route, "methods", None)
        path = getattr(route, "path", None)
        if not methods or path is None or path.startswith(("/docs", "/redoc", "/openapi")):
            continue
        for method in methods:
            if method != "HEAD":
                yield method, path


def test_route_table_matches_snapshot() -> None:
    """Every (method, path) pair the app serves is listed here; update deliberately when adding routes."""
    pairs = set(_walk(list(app.routes)))
    assert pairs == EXPECTED, f"route table changed: +{pairs - EXPECTED} -{EXPECTED - pairs}"
