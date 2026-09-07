"""Diff-scoped guard: no bare ``==``/``!=`` against a float literal in changed test asserts.

``assert result == 0.1 + 0.2`` is brittle by construction; ``pytest.approx``
is the house fix. Only assert statements on lines this changeset touched are
evaluated. Escape hatch: ``# discipline: float-compare <reason>`` on the line.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _check_runner import DiffScope, diff_scoped_cli  # noqa: E402
from _discipline import line_has_reasoned_waiver  # noqa: E402


def _is_float_literal(node: ast.expr) -> bool:
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        node = node.operand
    return isinstance(node, ast.Constant) and isinstance(node.value, float)


def _is_approx(node: ast.expr) -> bool:
    return isinstance(node, ast.Call) and (
        (isinstance(node.func, ast.Name) and node.func.id == "approx")
        or (isinstance(node.func, ast.Attribute) and node.func.attr == "approx")
    )


def find_violations(path: Path, source: str, changed: set[int]) -> list[str]:
    """Changed assert lines comparing a float literal with ``==``/``!=`` without approx."""
    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError:
        return []
    lines = source.splitlines()
    out: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assert) or node.lineno not in changed:
            continue
        if line_has_reasoned_waiver(lines[node.lineno - 1], "float-compare"):
            continue
        for cmp in (n for n in ast.walk(node.test) if isinstance(n, ast.Compare)):
            operands = [cmp.left, *cmp.comparators]
            for op, left, right in zip(cmp.ops, operands, operands[1:], strict=False):
                if not isinstance(op, ast.Eq | ast.NotEq):
                    continue
                if (_is_float_literal(left) or _is_float_literal(right)) and not (
                    _is_approx(left) or _is_approx(right)
                ):
                    out.append(
                        f"{path}:{node.lineno}: float equality in assert; use pytest.approx(...)"
                    )
    return out


def main(argv: list[str] | None = None) -> int:
    return diff_scoped_cli(
        argv,
        "Test float comparisons",
        find_violations,
        scope=DiffScope(("tests",), only_tests=True),
    )


if __name__ == "__main__":
    raise SystemExit(main())
