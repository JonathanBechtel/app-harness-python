"""Diff-scoped guard: changed test functions must carry a docstring.

CLAUDE.md asks every test for a one-line docstring naming the behaviour under
test and the expected outcome. Without enforcement that runs on the honour
system and drifts. Diff-scoped at LINE granularity: only a ``test_*`` function
whose span overlaps lines this changeset added or modified is evaluated, so
existing tests are never retrofitted wholesale.

Usage::

    python scripts/check_test_docstrings.py                      # vs HEAD
    python scripts/check_test_docstrings.py --against origin/main
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _check_runner import DiffScope, diff_scoped_cli  # noqa: E402


def find_violations(path: Path, source: str, changed: set[int]) -> list[str]:
    """Changed test functions in ``source`` lacking a docstring."""
    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError:
        return []
    out: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) or not node.name.startswith(
            "test_"
        ):
            continue
        end = node.end_lineno or node.lineno
        if not any(line in changed for line in range(node.lineno, end + 1)):
            continue
        doc = ast.get_docstring(node)
        if not doc or not doc.strip():
            out.append(
                f"{path}:{node.lineno}: {node.name} is missing a docstring (changed in this diff)"
            )
    return out


def main(argv: list[str] | None = None) -> int:
    return diff_scoped_cli(
        argv,
        "Test docstrings",
        find_violations,
        scope=DiffScope(("tests",), only_tests=True),
        footer="Add a one-line docstring: the behaviour under test and the expected outcome (CLAUDE.md).",
    )


if __name__ == "__main__":
    raise SystemExit(main())
