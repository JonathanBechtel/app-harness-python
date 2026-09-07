"""Unscoped-delete guard across import spellings, with the waiver escape hatch."""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest

from tests.unit._script_loader import load_script

guard = load_script("check_unscoped_delete")


@pytest.mark.parametrize(
    "source",
    [
        "from sqlalchemy import delete\nasync def f(db, M):\n    await db.execute(delete(M))\n",
        "from sqlalchemy import delete as sa_delete\nasync def f(db, M):\n    await db.execute(sa_delete(M))\n",
        "import sqlalchemy as sa\nasync def f(db, M):\n    await db.execute(sa.delete(M))\n",
        "def f(db, M):\n    db.query(M).delete()\n",
    ],
)
def test_each_spelling_is_flagged(tmp_path: Path, source: str) -> None:
    """Every bulk-delete spelling without a where clause is reported."""
    p = tmp_path / "m.py"
    p.write_text(source)
    assert guard.check_paths([p]), source


def test_scoped_and_instance_deletes_pass(tmp_path: Path) -> None:
    """`delete(M).where(...)`, chained where, and `db.delete(obj)` are all fine."""
    p = tmp_path / "m.py"
    p.write_text(
        dedent("""
        from sqlalchemy import delete
        async def f(db, M, obj):
            await db.execute(delete(M).where(M.id == 1))
            await db.execute(delete(M).execution_options(x=1).where(M.id == 2))
            await db.delete(obj)
    """).lstrip()
    )
    assert guard.check_paths([p]) == []


def test_waiver_requires_reason(tmp_path: Path) -> None:
    """A bare marker is not a waiver; a reasoned one is."""
    bare = tmp_path / "a.py"
    bare.write_text(
        "from sqlalchemy import delete\nasync def f(db, M):\n    await db.execute(delete(M))  # discipline: unscoped-delete\n"
    )
    assert guard.check_paths([bare])
    reasoned = tmp_path / "b.py"
    reasoned.write_text(
        "from sqlalchemy import delete\nasync def f(db, M):\n    await db.execute(delete(M))  # discipline: unscoped-delete demo table\n"
    )
    assert guard.check_paths([reasoned]) == []


def test_repo_is_clean() -> None:
    """The template contains no unscoped deletes."""
    assert guard.check_all() == []
