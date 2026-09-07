"""Diff-scoped migration-safety checker for Alembic revisions.

Failure this descends from: a release migration's non-concurrent ``CREATE
INDEX`` queued behind a long transaction; the deploy stalled in the lock
queue, the pool filled, public routes 500'd for over an hour. Deploy-time lock
contention should degrade the DEPLOY -- a fast, retryable failure -- never
production reads.

Rules, diff-scoped to revisions this changeset adds or edits:

  M1  ``op.create_index(...)`` passes ``postgresql_concurrently=True``.
  M2  A concurrent index build sits inside ``op.get_context().autocommit_block()``
      (Postgres rejects CONCURRENTLY inside a transaction, and env.py runs each
      revision in one). M1 without M2 turns a lock hazard into a guaranteed
      failed release, so both are required together.
  M3  Raw SQL ``op.execute("CREATE INDEX ...")`` obeys M1+M2 too (string scan
      scoped to executing calls, so docstrings discussing the hazard pass).
  M4  ``alembic/env.py`` keeps an EXECUTED ``lock_timeout`` statement and
      ``transaction_per_migration=True`` (checked whenever env.py is in the diff).
  M5  The migration graph has exactly one head.

Waiver: ``# discipline: migration-safety <reason>`` on the statement (small or
empty tables may build indexes non-concurrently).
"""

from __future__ import annotations

import argparse
import ast
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _astutil import module_aliases, resolved_call_name, trailing_name  # noqa: E402
from _check_runner import merge_base, report, untracked_files  # noqa: E402
from _discipline import statement_has_reasoned_waiver  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
VERSIONS = REPO / "alembic" / "versions"
ENV_PY = REPO / "alembic" / "env.py"
RULE = "migration-safety"
_CREATE_INDEX = re.compile(r"\bCREATE\s+(UNIQUE\s+)?INDEX\b", re.IGNORECASE)
_CONCURRENTLY = re.compile(r"\bCONCURRENTLY\b", re.IGNORECASE)


def changed_migration_files(against: str) -> list[Path]:
    """Revisions (and env.py) added or modified vs the merge base."""
    base = merge_base(against)
    out = subprocess.run(
        ["git", "diff", "--name-only", "--diff-filter=AM", base, "--", "alembic/"],
        capture_output=True,
        text=True,
        cwd=REPO,
        check=True,
    )
    files = out.stdout.splitlines() + untracked_files(("alembic/",))
    return [REPO / line for line in files if line.endswith(".py")]


def _inside_autocommit(stack: list[ast.AST]) -> bool:
    for parent in stack:
        if isinstance(parent, ast.With | ast.AsyncWith):
            for item in parent.items:
                expr = item.context_expr
                if isinstance(expr, ast.Call) and trailing_name(expr.func) == "autocommit_block":
                    return True
    return False


def _walk_with_parents(tree: ast.AST) -> list[tuple[ast.AST, list[ast.AST]]]:
    result: list[tuple[ast.AST, list[ast.AST]]] = []

    def visit(node: ast.AST, stack: list[ast.AST]) -> None:
        result.append((node, stack))
        for child in ast.iter_child_nodes(node):
            visit(child, [*stack, node])

    visit(tree, [])
    return result


def check_revision(path: Path) -> list[str]:
    """M1-M3 violations in one revision file."""
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    lines = source.splitlines()
    aliases = module_aliases(tree)
    rel = path.relative_to(REPO).as_posix() if path.is_relative_to(REPO) else path.as_posix()
    out: list[str] = []
    for node, stack in _walk_with_parents(tree):
        if not isinstance(node, ast.Call):
            continue
        stmt = next((p for p in reversed(stack) if isinstance(p, ast.stmt)), None)
        first = stmt.lineno if stmt else node.lineno
        last = (stmt.end_lineno or first) if stmt else first
        if statement_has_reasoned_waiver(lines, first, last, RULE):
            continue
        out += _check_call(rel, node, resolved_call_name(node, aliases), _inside_autocommit(stack))
    return out


def _check_call(rel: str, node: ast.Call, name: str | None, in_autocommit: bool) -> list[str]:
    if name == "create_index":
        concurrent = any(
            k.arg == "postgresql_concurrently"
            and isinstance(k.value, ast.Constant)
            and k.value.value is True
            for k in node.keywords
        )
        if not concurrent:
            return [
                f"{rel}:{node.lineno}: M1 op.create_index must pass postgresql_concurrently=True"
            ]
        if not in_autocommit:
            return [
                f"{rel}:{node.lineno}: M2 concurrent index build must be inside op.get_context().autocommit_block()"
            ]
        return []
    if name in {"execute", "exec_driver_sql"} and node.args:
        sql = _string_value(node.args[0])
        if sql and _CREATE_INDEX.search(sql):
            if not _CONCURRENTLY.search(sql):
                return [f"{rel}:{node.lineno}: M3 raw CREATE INDEX must use CONCURRENTLY"]
            if not in_autocommit:
                return [
                    f"{rel}:{node.lineno}: M3 raw CREATE INDEX CONCURRENTLY must be inside autocommit_block()"
                ]
    return []


def _string_value(node: ast.expr) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.Call) and trailing_name(node.func) == "text" and node.args:
        return _string_value(node.args[0])
    if isinstance(node, ast.JoinedStr):
        return "".join(
            v.value for v in node.values if isinstance(v, ast.Constant) and isinstance(v.value, str)
        )
    return None


def check_env() -> list[str]:
    """M4: env.py executes a lock_timeout and configures transaction_per_migration."""
    source = ENV_PY.read_text(encoding="utf-8")
    tree = ast.parse(source)
    out: list[str] = []
    executed_lock_timeout = any(
        isinstance(n, ast.Call)
        and trailing_name(n.func) == "execute"
        and n.args
        and "lock_timeout" in (_string_value(n.args[0]) or "")
        for n in ast.walk(tree)
    )
    if not executed_lock_timeout:
        out.append(
            "alembic/env.py: M4 must EXECUTE a `SELECT set_config('lock_timeout', ...)` statement before running migrations"
        )
    per_migration = any(
        isinstance(n, ast.keyword)
        and n.arg == "transaction_per_migration"
        and isinstance(n.value, ast.Constant)
        and n.value.value is True
        for n in ast.walk(tree)
    )
    if not per_migration:
        out.append(
            "alembic/env.py: M4 context.configure(...) must set transaction_per_migration=True"
        )
    return out


def _revision_graph() -> dict[str, set[str]]:
    """Map revision id -> set of down_revision ids for every migration file."""
    revisions: dict[str, set[str]] = {}
    for path in VERSIONS.glob("*.py"):
        rev, down = _revision_ids(ast.parse(path.read_text(encoding="utf-8")))
        if rev:
            revisions[rev] = down
    return revisions


def _revision_ids(tree: ast.Module) -> tuple[str | None, set[str]]:
    rev: str | None = None
    down: set[str] = set()
    for node in tree.body:
        if not isinstance(node, ast.Assign | ast.AnnAssign):
            continue
        target = node.targets[0] if isinstance(node, ast.Assign) else node.target
        value = node.value
        if not isinstance(target, ast.Name) or value is None:
            continue
        if target.id == "revision" and isinstance(value, ast.Constant):
            rev = str(value.value)
        elif target.id == "down_revision":
            if isinstance(value, ast.Constant) and value.value:
                down.add(str(value.value))
            elif isinstance(value, ast.Tuple | ast.List):
                down.update(str(e.value) for e in value.elts if isinstance(e, ast.Constant))
    return rev, down


def check_single_head() -> list[str]:
    """M5: exactly one head in the revision graph (zero revisions is fine)."""
    revisions = _revision_graph()
    if not revisions:
        return []
    parents: set[str] = set().union(*revisions.values())
    heads = [r for r in revisions if r not in parents]
    if len(heads) != 1:
        return [
            f"alembic/versions: M5 expected exactly one head, found {len(heads)}: {sorted(heads)}; add a merge revision"
        ]
    return []


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--against", default="HEAD")
    args = parser.parse_args(argv)
    try:
        changed = changed_migration_files(args.against)
    except subprocess.CalledProcessError as exc:
        print(f"migration safety: git failed: {exc}", file=sys.stderr)
        return 1
    violations: list[str] = []
    for path in changed:
        if path == ENV_PY:
            violations += check_env()
        elif path.parent == VERSIONS:
            violations += check_revision(path)
    violations += check_single_head()
    return report(
        "Migration safety",
        violations,
        ok_message="migration safety: OK",
        footer="See scripts/check_migration_safety.py; waive per-statement with `# discipline: migration-safety <reason>`.",
    )


if __name__ == "__main__":
    raise SystemExit(main())
