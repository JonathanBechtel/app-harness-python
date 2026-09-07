"""Disallow empty method bodies (``pass`` / ``...``) in concrete classes.

An empty override silently swallows the behaviour it replaced. ``Protocol``
classes and ``@abstractmethod`` members are exempt; so is a method whose body is
a docstring only (that is documentation, not a stub).
"""

from __future__ import annotations

import ast
import sys
from collections.abc import Sequence
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _check_runner import CheckSpec, git_tracked_files, run_cli  # noqa: E402


def _matches(node: ast.AST, name: str) -> bool:
    return (isinstance(node, ast.Name) and node.id == name) or (
        isinstance(node, ast.Attribute) and node.attr == name
    )


def _is_stub(member: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    body = [
        s
        for s in member.body
        if not (
            isinstance(s, ast.Expr)
            and isinstance(s.value, ast.Constant)
            and isinstance(s.value.value, str)
        )
    ]
    if len(body) != 1:
        return False
    stmt = body[0]
    return isinstance(stmt, ast.Pass) or (
        isinstance(stmt, ast.Expr)
        and isinstance(stmt.value, ast.Constant)
        and stmt.value.value is Ellipsis
    )


def check_file(path: Path) -> list[str]:
    """Violations in one file."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    errors: list[str] = []
    for cls in (n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)):
        if any(_matches(b, "Protocol") for b in cls.bases):
            continue
        for member in cls.body:
            if not isinstance(member, ast.FunctionDef | ast.AsyncFunctionDef):
                continue
            if any(
                _matches(d, "abstractmethod") or _matches(d, "overload")
                for d in member.decorator_list
            ):
                continue
            if _is_stub(member):
                errors.append(
                    f"{path}:{member.lineno}: EMPTY001 {cls.name}.{member.name} has an empty body"
                )
    return errors


def check_paths(paths: Sequence[Path]) -> list[str]:
    """Violations for the given paths."""
    out: list[str] = []
    for p in paths:
        if p.suffix == ".py" and p.is_file():
            out += check_file(p)
    return out


def check_all() -> list[str]:
    """Violations across app/ and tests/."""
    files = git_tracked_files(r"^(app|tests)/")
    if not files:
        raise ValueError("no files matched app|tests -- guard would pass vacuously")
    return check_paths(files)


def main(argv: list[str]) -> int:
    return run_cli(argv, CheckSpec(check_all, check_paths, "Empty method stubs", Path(__file__)))


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
