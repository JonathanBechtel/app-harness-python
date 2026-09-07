"""Enforce UPPER_CASE enum members in Alembic migrations (ENUM001).

SQLAlchemy persists a Python ``Enum`` column by member NAME (``ACTIVE``), not
value (``"active"``). A migration declaring ``sa.Enum("active", ...)`` creates
a column that rejects every insert the ORM makes -- a failure only a live
database surfaces. Escape hatches: ``values_callable=`` on the call, or
``# noqa: ENUM001`` on the line.
"""

from __future__ import annotations

import ast
import sys
from collections.abc import Sequence
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _check_runner import CheckSpec, git_tracked_files, run_cli  # noqa: E402

_ENUM_CALLS = {"Enum", "ENUM"}


def check_file(path: Path) -> list[str]:
    """ENUM001 violations in one migration."""
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    lines = source.splitlines()
    out: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = (
            node.func.attr
            if isinstance(node.func, ast.Attribute)
            else getattr(node.func, "id", None)
        )
        if name not in _ENUM_CALLS or any(k.arg == "values_callable" for k in node.keywords):
            continue
        if "noqa: ENUM001" in lines[node.lineno - 1]:
            continue
        for arg in node.args:
            if (
                isinstance(arg, ast.Constant)
                and isinstance(arg.value, str)
                and arg.value != arg.value.upper()
            ):
                out.append(
                    f"{path}:{arg.lineno}: ENUM001 enum member {arg.value!r} is not UPPER_CASE"
                )
    return out


def check_paths(paths: Sequence[Path]) -> list[str]:
    """Violations for the given paths."""
    out: list[str] = []
    for p in paths:
        if p.suffix == ".py" and p.is_file():
            out += check_file(p)
    return out


def check_all() -> list[str]:
    """Violations across every migration (an empty versions/ dir is fine)."""
    return check_paths(git_tracked_files(r"^alembic/versions/"))


def main(argv: list[str]) -> int:
    return run_cli(argv, CheckSpec(check_all, check_paths, "Migration enum case", Path(__file__)))


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
