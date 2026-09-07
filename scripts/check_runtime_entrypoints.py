"""Guard the ``app/cli`` (shipped runtime jobs) vs ``scripts/`` (operator tooling) boundary.

E1  No deploy configuration (``deploy/**``, ``.github/workflows/**``,
    ``Dockerfile``) invokes a ``scripts/`` path as a runtime command.
    Runtime jobs run as ``python -m app.cli.<module>``.
E2  Nothing under ``app/`` imports ``scripts.*``; the shipped package must
    not depend on operator tooling. Baseline in ``KNOWN_APP_IMPORTS_SCRIPTS``
    may shrink, never grow (currently empty).
E3  Nothing under ``app/`` references a path ``.dockerignore`` excludes
    (``scripts/``, ``tests/``, ``docs/`` ...). Such a read passes CI and
    breaks at runtime in the container. The excluded set is read from
    ``.dockerignore`` itself so the two cannot drift. Docstrings/comments are
    exempt; string literals and Path segments are not.
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _astutil import docstring_node_ids  # noqa: E402
from _check_runner import git_tracked_files, report  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
KNOWN_APP_IMPORTS_SCRIPTS: frozenset[str] = frozenset()
_DEPLOY_GLOBS = ("deploy/**/*", ".github/workflows/*.yml", ".github/workflows/*.yaml", "Dockerfile")
_SCRIPTS_INVOCATION = re.compile(r"(python[0-9.]*\s+|\bbash\s+|\bsh\s+|^\s*-\s*)scripts/[\w./-]+")


def excluded_dirs() -> set[str]:
    """Top-level directories .dockerignore excludes (trailing-slash entries)."""
    text = (REPO / ".dockerignore").read_text(encoding="utf-8")
    dirs: set[str] = set()
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith(("#", "!")) or "*" in line or line.startswith("."):
            continue
        if line.endswith("/"):
            dirs.add(line.rstrip("/"))
    return dirs


def check_e1() -> list[str]:
    out: list[str] = []
    for pattern in _DEPLOY_GLOBS:
        for path in REPO.glob(pattern):
            if not path.is_file() or path.suffix == ".md":
                continue
            for i, line in enumerate(
                path.read_text(encoding="utf-8", errors="ignore").splitlines(), 1
            ):
                stripped = line.strip()
                if stripped.startswith("#"):
                    continue
                if (
                    "make " in stripped
                    or "pre-commit" in stripped
                    or "pytest" in stripped
                    or "ruff" in stripped
                    or "check_" in stripped
                ):
                    continue  # CI steps legitimately run checks from a checkout
                if _SCRIPTS_INVOCATION.search(stripped) and "bootstrap_env" not in stripped:
                    out.append(
                        f"{path.relative_to(REPO).as_posix()}:{i}: E1 deploy config invokes scripts/ as a runtime command; use `python -m app.cli.<module>`"
                    )
    return out


def check_e2_e3(app_files: list[Path]) -> list[str]:
    out: list[str] = []
    excluded = excluded_dirs()
    for path in app_files:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
        docstrings = docstring_node_ids(tree)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import | ast.ImportFrom):
                names = (
                    [a.name for a in node.names]
                    if isinstance(node, ast.Import)
                    else [node.module or ""]
                )
                for name in names:
                    if name == "scripts" or name.startswith("scripts."):
                        key = f"{path}:{name}"
                        if key not in KNOWN_APP_IMPORTS_SCRIPTS:
                            out.append(
                                f"{path}:{node.lineno}: E2 app/ must not import `{name}` (operator tooling)"
                            )
            elif (
                isinstance(node, ast.Constant)
                and isinstance(node.value, str)
                and id(node) not in docstrings
            ):
                value = node.value
                for d in excluded:
                    if value == d or value.startswith(f"{d}/") or f"/{d}/" in value:
                        out.append(
                            f"{path}:{node.lineno}: E3 references `{value}`, which .dockerignore excludes from the image"
                        )
                        break
    return out


def main() -> int:
    app_files = git_tracked_files(r"^app/")
    if not app_files:
        raise SystemExit("no files matched app/ -- guard would pass vacuously")
    violations = check_e1() + check_e2_e3(app_files)
    return report(
        "Runtime entrypoint boundary",
        violations,
        ok_message="runtime entrypoints: OK",
        footer="Shipped code lives in app/ and reads only app/data; operator tooling lives in scripts/.",
    )


if __name__ == "__main__":
    raise SystemExit(main())
