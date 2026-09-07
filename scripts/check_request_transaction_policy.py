"""Ban explicit ``commit()`` / ``rollback()`` in request-bounded code.

Routes and services use ``async with db.begin(): ...`` so commit/rollback are
structural, not remembered. Runtime jobs (``app/cli``) and ``scripts/`` may
still manage transactions explicitly. Matches the attribute form
(``db.commit()``) and, through the alias map, a locally rebound name.
"""

from __future__ import annotations

import ast
import sys
from collections.abc import Sequence
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _astutil import module_aliases, resolve, trailing_name  # noqa: E402
from _check_runner import CheckSpec, git_tracked_files, run_cli  # noqa: E402

_FORBIDDEN = {"commit", "rollback"}
_SCOPE = r"^app/(api|web|services)/"


def _find(paths: Sequence[Path]) -> list[str]:
    violations: list[str] = []
    for path in paths:
        if path.suffix != ".py" or not path.is_file():
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        aliases = module_aliases(tree)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            name = (
                node.func.attr
                if isinstance(node.func, ast.Attribute)
                else resolve(trailing_name(node.func), aliases)
            )
            if name in _FORBIDDEN:
                violations.append(
                    f"{path}:{node.lineno}: explicit {name}() in request-bounded code"
                )
    return sorted(violations)


def check_paths(paths: Sequence[Path]) -> list[str]:
    """Violations for the given paths."""
    return _find(paths)


def check_all() -> list[str]:
    """Violations across every tracked route/service module."""
    files = git_tracked_files(_SCOPE)
    if not files:
        raise ValueError("no files matched app/(api|web|services) -- guard would pass vacuously")
    return _find(files)


def main(argv: list[str]) -> int:
    return run_cli(
        argv,
        CheckSpec(
            check_all,
            check_paths,
            "Request transaction policy",
            Path(__file__),
            footer="Use `async with db.begin(): ...` in routes/services; explicit commit/rollback belongs in app/cli or scripts.",
        ),
    )


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
