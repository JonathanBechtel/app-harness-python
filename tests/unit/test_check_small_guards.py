"""Empty-stub and enum-case guards fire on seeded violations."""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

from tests.unit._script_loader import load_script

stubs = load_script("check_empty_method_stubs")
enums = load_script("check_migration_enum_case")


def test_empty_stub_flagged_but_protocol_and_abstract_exempt(tmp_path: Path) -> None:
    """A `pass` body in a concrete class is EMPTY001; Protocol members and abstractmethods are not."""
    p = tmp_path / "m.py"
    p.write_text(
        dedent('''
        from typing import Protocol
        from abc import abstractmethod
        class Concrete:
            def a(self):
                pass
            def b(self):
                """Documented but empty."""
                ...
            @abstractmethod
            def c(self): ...
        class P(Protocol):
            def d(self): ...
    ''').lstrip()
    )
    out = stubs.check_paths([p])
    assert len(out) == 2 and all("EMPTY001" in v for v in out), out


def test_lowercase_enum_member_flagged(tmp_path: Path) -> None:
    """`sa.Enum("active")` in a migration is ENUM001; UPPER_CASE and values_callable pass."""
    p = tmp_path / "0001_x.py"
    p.write_text(
        dedent("""
        import sqlalchemy as sa
        bad = sa.Enum("active", "paused", name="s")
        good = sa.Enum("ACTIVE", name="s2")
        ok = sa.Enum("active", name="s3", values_callable=lambda e: [m.value for m in e])
        noqa = sa.Enum("active", name="s4")  # noqa: ENUM001
    """).lstrip()
    )
    out = enums.check_paths([p])
    assert len(out) == 2, out


def test_repo_is_clean() -> None:
    """The template has no stubs and no migrations with bad enum case."""
    assert stubs.check_all() == []
    assert enums.check_all() == []
