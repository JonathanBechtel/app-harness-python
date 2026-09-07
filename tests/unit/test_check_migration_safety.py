"""Migration-safety rules on seeded revisions, plus the live env.py and head check."""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

from tests.unit._script_loader import load_script

guard = load_script("check_migration_safety")


def _rev(tmp_path: Path, body: str) -> Path:
    p = tmp_path / "0001_x.py"
    p.write_text(dedent(body).lstrip())
    return p


def test_non_concurrent_index_is_m1(tmp_path: Path) -> None:
    """op.create_index without postgresql_concurrently=True is M1."""
    out = guard.check_revision(
        _rev(
            tmp_path,
            """
        from alembic import op
        def upgrade():
            op.create_index("ix", "t", ["c"])
    """,
        )
    )
    assert any("M1" in v for v in out), out


def test_concurrent_outside_autocommit_is_m2(tmp_path: Path) -> None:
    """Concurrent build outside autocommit_block is M2; inside it passes."""
    out = guard.check_revision(
        _rev(
            tmp_path,
            """
        from alembic import op
        def upgrade():
            op.create_index("ix", "t", ["c"], postgresql_concurrently=True)
    """,
        )
    )
    assert any("M2" in v for v in out), out
    ok = guard.check_revision(
        _rev(
            tmp_path,
            """
        from alembic import op
        def upgrade():
            with op.get_context().autocommit_block():
                op.create_index("ix", "t", ["c"], postgresql_concurrently=True)
    """,
        )
    )
    assert ok == []


def test_raw_sql_index_is_m3_but_docstring_is_not(tmp_path: Path) -> None:
    """op.execute("CREATE INDEX ...") is scanned; prose mentioning CREATE INDEX is not."""
    out = guard.check_revision(
        _rev(
            tmp_path,
            '''
        """This revision discusses CREATE INDEX hazards."""
        from alembic import op
        def upgrade():
            op.execute("CREATE INDEX ix ON t (c)")
    ''',
        )
    )
    assert len([v for v in out if "M3" in v]) == 1, out


def test_waiver_exempts_statement(tmp_path: Path) -> None:
    """A reasoned migration-safety waiver exempts a small-table index."""
    out = guard.check_revision(
        _rev(
            tmp_path,
            """
        from alembic import op
        def upgrade():
            # discipline: migration-safety lookup table with <100 rows
            op.create_index("ix", "t", ["c"])
    """,
        )
    )
    assert out == []


def test_env_and_heads_are_safe() -> None:
    """The template's env.py executes lock_timeout and uses transaction_per_migration; one head."""
    assert guard.check_env() == []
    assert guard.check_single_head() == []
