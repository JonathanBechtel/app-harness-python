"""Ban ``delete(Model)`` with no ``.where(...)`` — retain history by default.

A bulk delete with no filter empties a table. "Wipe clean and recompute" is
the anti-pattern this guards against: it destroys the time axis. Recognised
under every spelling (``delete``, ``sa_delete``, ``sa.delete``,
``sqlalchemy.sql.delete``, legacy ``query(Model).delete()``); the ORM instance
delete ``db.delete(obj)`` is inherently scoped and not flagged. Raw SQL is out
of reach and a known gap.

Escape hatch (mandatory reason)::

    await db.execute(delete(Demo))  # discipline: unscoped-delete demo table, seed script
"""

from __future__ import annotations

import ast
import sys
from collections.abc import Sequence
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _astutil import module_aliases, resolve, trailing_name  # noqa: E402
from _check_runner import CheckSpec, git_tracked_files, run_cli  # noqa: E402
from _discipline import statement_has_reasoned_waiver  # noqa: E402

RULE = "unscoped-delete"


def _sqlalchemy_bound_names(tree: ast.AST) -> set[str]:
    """Local names bound to sqlalchemy's ``delete`` (any alias) or to sqlalchemy modules."""
    names: set[str] = set()
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.ImportFrom)
            and node.module
            and node.module.startswith("sqlalchemy")
        ):
            names.update(a.asname or a.name for a in node.names if a.name == "delete")
        elif isinstance(node, ast.ImportFrom) and node.module == "sqlmodel":
            names.update(a.asname or a.name for a in node.names if a.name == "delete")
        elif isinstance(node, ast.Import):
            names.update(
                (a.asname or a.name).split(".")[0]
                for a in node.names
                if a.name.startswith("sqlalchemy")
            )
    return names


def _is_bulk_delete(call: ast.Call, sa_names: set[str], aliases: dict[str, str]) -> bool:
    func = call.func
    if isinstance(func, ast.Name):
        return resolve(func.id, aliases) in sa_names or func.id in sa_names
    if isinstance(func, ast.Attribute) and func.attr == "delete":
        root = func.value
        while isinstance(root, ast.Attribute):
            root = root.value
        if isinstance(root, ast.Name) and root.id in sa_names:
            return True
        # legacy query(Model).delete()
        if isinstance(func.value, ast.Call) and trailing_name(func.value.func) == "query":
            return True
    return False


def _has_where(node: ast.expr) -> bool:
    while isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
        if node.func.attr in {"where", "filter", "filter_by"}:
            return True
        node = node.func.value
    return False


def check_file(path: Path) -> list[str]:
    """Unscoped bulk deletes in one file."""
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    lines = source.splitlines()
    sa_names = _sqlalchemy_bound_names(tree)
    aliases = module_aliases(tree)
    out: list[str] = []
    for stmt in (n for n in ast.walk(tree) if isinstance(n, ast.stmt)):
        for node in ast.walk(stmt):
            if not isinstance(node, ast.Call) or not _is_bulk_delete(node, sa_names, aliases):
                continue
            # walk up the fluent chain from this call to see if a .where wraps it
            if _has_where(node) or _wrapped_by_where(stmt, node):
                continue
            if statement_has_reasoned_waiver(
                lines, stmt.lineno, stmt.end_lineno or stmt.lineno, RULE
            ):
                continue
            out.append(
                f"{path}:{node.lineno}: unscoped delete(...) with no .where(); retain history by default"
            )
            break
    return out


def _wrapped_by_where(stmt: ast.stmt, target: ast.Call) -> bool:
    for node in ast.walk(stmt):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr in {"where", "filter", "filter_by"}
        ):
            inner = node.func.value
            while isinstance(inner, ast.Call) and isinstance(inner.func, ast.Attribute):
                if inner is target:
                    return True
                inner = inner.func.value
            if inner is target:
                return True
    return False


def check_paths(paths: Sequence[Path]) -> list[str]:
    """Violations for the given paths."""
    out: list[str] = []
    for p in paths:
        if p.suffix == ".py" and p.is_file():
            out += check_file(p)
    return out


def check_all() -> list[str]:
    """Violations across app/ and scripts/."""
    files = git_tracked_files(r"^(app|scripts)/")
    if not files:
        raise ValueError("no files matched app|scripts -- guard would pass vacuously")
    return check_paths(files)


def main(argv: list[str]) -> int:
    return run_cli(
        argv,
        CheckSpec(
            check_all,
            check_paths,
            "Unscoped delete ban",
            Path(__file__),
            footer="Add .where(...), or waive with `# discipline: unscoped-delete <reason>`.",
        ),
    )


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
