"""Transaction-policy guard fires on commit/rollback, including via a rebound name."""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

from tests.unit._script_loader import load_script

guard = load_script("check_request_transaction_policy")


def test_flags_commit_and_rebound_commit(tmp_path: Path) -> None:
    """Both `db.commit()` and a locally bound alias of it are reported."""
    p = tmp_path / "svc.py"
    p.write_text(
        dedent("""
        async def f(db):
            await db.commit()
            _flush = db.rollback
            await _flush()
    """).lstrip()
    )
    out = guard.check_paths([p])
    assert len(out) == 2, out


def test_begin_block_is_fine(tmp_path: Path) -> None:
    """`async with db.begin()` is the sanctioned form and is not reported."""
    p = tmp_path / "svc.py"
    p.write_text("async def f(db):\n    async with db.begin():\n        pass\n")
    assert guard.check_paths([p]) == []


def test_repo_is_clean() -> None:
    """No request-bounded module in the template commits or rolls back explicitly."""
    assert guard.check_all() == []
