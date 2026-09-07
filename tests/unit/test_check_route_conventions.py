"""Route-conventions guard: each rule fires on a seeded violation and stays quiet on compliant code."""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

from tests.unit._script_loader import load_script

guard = load_script("check_route_conventions")


def _run(source: str, tmp_path: Path) -> list[str]:
    p = tmp_path / "routes_sample.py"
    p.write_text(dedent(source).lstrip(), encoding="utf-8")
    return guard.check_paths([p])


def test_r1_missing_response_shape(tmp_path: Path) -> None:
    """A decorator without response_model/response_class trips R1."""
    out = _run(
        """
        @router.get("/x")
        async def handler():
            return {}
    """,
        tmp_path,
    )
    assert any("[R1]" in v for v in out), out


def test_r2_write_without_status_code(tmp_path: Path) -> None:
    """A JSON POST without status_code trips R2."""
    out = _run(
        """
        @router.post("/x", response_model=dict)
        async def handler():
            return {}
    """,
        tmp_path,
    )
    assert any("[R2]" in v for v in out), out


def test_r3_bare_async_session_even_when_aliased(tmp_path: Path) -> None:
    """`AsyncSession as Session` with a Depends default still trips R3; DbSession passes."""
    out = _run(
        """
        from sqlalchemy.ext.asyncio import AsyncSession as Session
        from fastapi import Depends
        @router.get("/x", response_model=dict)
        async def handler(db: Session = Depends(get_session)):
            return {}
    """,
        tmp_path,
    )
    assert any("[R3]" in v for v in out), out
    clean = _run(
        """
        from app.api.deps import DbSession
        @router.get("/x", response_model=dict)
        async def handler(db: DbSession):
            return {}
    """,
        tmp_path,
    )
    assert clean == []


def test_r4_template_context_needs_request(tmp_path: Path) -> None:
    """A TemplateResponse whose context lacks `request` trips R4."""
    out = _run(
        """
        @router.get("/", response_class=HTMLResponse)
        async def index(request: Request):
            return templates.TemplateResponse(request, "index.html", {"env": "x"})
    """,
        tmp_path,
    )
    assert any("[R4]" in v for v in out), out


def test_waiver_silences_decorator_rules(tmp_path: Path) -> None:
    """A reasoned discipline waiver on the decorator exempts R1/R2."""
    out = _run(
        """
        @router.post("/x")  # discipline: route-conventions webhook echoes raw bytes
        async def handler():
            return {}
    """,
        tmp_path,
    )
    assert out == []


def test_repo_is_clean() -> None:
    """The template's own routes satisfy every rule."""
    assert guard.check_all() == []
