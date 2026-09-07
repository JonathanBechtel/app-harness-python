#!/usr/bin/env python3
"""Cross-platform task runner: the single definition of every project task.

    python tasks.py <task> [KEY=VALUE ...]     # any OS
    make <task> [KEY=VALUE ...]                # thin shim over this file (macOS/Linux/WSL)

Why Python and not the Makefile itself: the team runs Windows, macOS and Linux,
and Windows has neither `make` nor bash by default. Every task here is a list
of subprocess arguments (no shell), so it behaves identically everywhere.
Tools are resolved from the active virtualenv first.

Every guard task is mirrored in .pre-commit-config.yaml and .github/workflows/ci.yml
with identical scope; tests/unit/test_guard_wiring.py asserts they agree.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parent
PY = sys.executable
IS_WINDOWS = os.name == "nt"


@dataclass(frozen=True)
class Task:
    name: str
    help: str
    fn: Callable[[dict[str, str]], int]


TASKS: dict[str, Task] = {}


def task(
    name: str, help_text: str
) -> Callable[[Callable[[dict[str, str]], int]], Callable[[dict[str, str]], int]]:
    """Register a task under ``name``."""

    def register(fn: Callable[[dict[str, str]], int]) -> Callable[[dict[str, str]], int]:
        TASKS[name] = Task(name, help_text, fn)
        return fn

    return register


# ---------------------------------------------------------------- helpers


def tool(name: str) -> str:
    """Path to a console script in the active environment, else the bare name."""
    bin_dir = Path(PY).parent
    candidate = bin_dir / (f"{name}.exe" if IS_WINDOWS else name)
    return str(candidate) if candidate.exists() else (shutil.which(name) or name)


def run(*cmd: str, env: dict[str, str] | None = None, check: bool = True) -> int:
    """Run a command from the repo root, streaming output; return its exit code."""
    printable = " ".join(cmd)
    print(f"$ {printable}", flush=True)
    merged = {**os.environ, **(env or {})}
    result = subprocess.run(list(cmd), cwd=REPO, env=merged, check=False)
    if check and result.returncode != 0:
        raise SystemExit(result.returncode)
    return result.returncode


def run_all(*cmds: tuple[str, ...]) -> int:
    """Run several commands, stopping at the first failure."""
    for cmd in cmds:
        run(*cmd)
    return 0


def param(params: dict[str, str], key: str, default: str) -> str:
    return params.get(key) or os.environ.get(key) or default


def git_sha() -> str:
    out = subprocess.run(
        ["git", "rev-parse", "--verify", "--quiet", "HEAD"],
        capture_output=True,
        text=True,
        cwd=REPO,
        check=False,
    )
    return out.stdout.strip() or "local"


def _required(params: dict[str, str], key: str, hint: str) -> str:
    value = param(params, key, "")
    if not value:
        print(f"[error] set {key}={hint}", file=sys.stderr)
        raise SystemExit(2)
    return value


# ---------------------------------------------------------------- setup / run


@task("help", "List tasks")
def _help(_: dict[str, str]) -> int:
    width = max(len(n) for n in TASKS)
    print("Usage: python tasks.py <task> [KEY=VALUE ...]   (or: make <task>)\n")
    for name, t in TASKS.items():
        print(f"  {name:<{width}}  {t.help}")
    return 0


@task("bootstrap", "Provision a clean machine to CI parity (venv, deps, Postgres, .env, hooks)")
def _bootstrap(params: dict[str, str]) -> int:
    extra = [a for a in params.get("_positional", "").split() if a]
    return run(PY, "scripts/bootstrap_env.py", *extra)


@task("dev", "Start the API with autoreload (HOST, PORT)")
def _dev(params: dict[str, str]) -> int:
    return run(
        PY,
        "-m",
        "uvicorn",
        "app.main:app",
        "--reload",
        "--host",
        param(params, "HOST", "0.0.0.0"),
        "--port",
        param(params, "PORT", "8000"),
    )


@task("run", "Start the API without reload (production-like)")
def _run(params: dict[str, str]) -> int:
    return run(
        PY,
        "-m",
        "uvicorn",
        "app.main:app",
        "--host",
        param(params, "HOST", "0.0.0.0"),
        "--port",
        param(params, "PORT", "8000"),
    )


# ---------------------------------------------------------------- lint / type


@task("fmt", "Format with ruff")
def _fmt(_: dict[str, str]) -> int:
    return run(tool("ruff"), "format", ".")


@task("lint", "Lint with ruff")
def _lint(_: dict[str, str]) -> int:
    return run(tool("ruff"), "check", ".")


@task("fix", "Apply ruff autofixes")
def _fix(_: dict[str, str]) -> int:
    return run(tool("ruff"), "check", "--fix", ".")


@task("typecheck", "mypy over the whole shipped package (CI runs exactly this)")
def _typecheck(_: dict[str, str]) -> int:
    return run(tool("mypy"), "app")


@task("precommit", "Run every pre-commit hook over the whole tree")
def _precommit(_: dict[str, str]) -> int:
    return run(tool("pre-commit"), "run", "-a")


# ---------------------------------------------------------------- guards


@task("lint.imports", "Structural import contracts ([tool.importlinter] in pyproject.toml)")
def _lint_imports(_: dict[str, str]) -> int:
    return run(tool("lint-imports"))


@task(
    "lint.complexity",
    "Per-file complexity ratchet vs complexity-baseline.json (counts may only fall)",
)
def _lint_complexity(_: dict[str, str]) -> int:
    return run(PY, "scripts/check_complexity_ratchet.py")


@task("lint.complexity.update", "Rewrite the complexity baseline after simplifying code")
def _lint_complexity_update(_: dict[str, str]) -> int:
    return run(PY, "scripts/check_complexity_ratchet.py", "--update")


@task("lint.filesize", "Diff-scoped file-size ratchet, enforced against BASE (default origin/main)")
def _lint_filesize(params: dict[str, str]) -> int:
    return run(
        PY,
        "scripts/check_file_size_ratchet.py",
        "--against",
        param(params, "BASE", "origin/main"),
        "--enforce",
    )


@task(
    "lint.filesize.report", "Waiver census: app/ files carrying a file-size waiver and their sizes"
)
def _lint_filesize_report(_: dict[str, str]) -> int:
    return run(PY, "scripts/check_file_size_ratchet.py", "--report")


@task(
    "lint.migrations", "New Alembic revisions build indexes concurrently inside an autocommit block"
)
def _lint_migrations(params: dict[str, str]) -> int:
    return run(
        PY, "scripts/check_migration_safety.py", "--against", param(params, "BASE", "origin/main")
    )


@task(
    "lint.migrations.roundtrip",
    "upgrade -> downgrade base -> assert schema empty -> upgrade (ROUNDTRIP_DATABASE_URL must be disposable)",
)
def _lint_migrations_roundtrip(params: dict[str, str]) -> int:
    url = _required(
        params,
        "ROUNDTRIP_DATABASE_URL",
        "postgresql+asyncpg://... (a DISPOSABLE database; this DROPs everything in it)",
    )
    env = {"DATABASE_URL": url, "APP_ENV": "stage"}
    alembic = tool("alembic")
    run(alembic, "upgrade", "head", env=env)
    run(alembic, "downgrade", "base", env=env)
    run(PY, "scripts/check_migration_teardown_residue.py", env=env)
    return run(alembic, "upgrade", "head", env=env)


@task("lint.duplication", "Diff-scoped duplicate-code gate (pylint R0801, % of changed lines)")
def _lint_duplication(params: dict[str, str]) -> int:
    return run(
        PY, "scripts/check_duplicate_code.py", "--against", param(params, "BASE", "origin/main")
    )


@task("lint.test-docstrings", "Changed test functions must carry a docstring")
def _lint_test_docstrings(params: dict[str, str]) -> int:
    return run(
        PY, "scripts/check_test_docstrings.py", "--against", param(params, "BASE", "origin/main")
    )


@task("lint.test-float", "Changed test asserts must use pytest.approx for float equality")
def _lint_test_float(params: dict[str, str]) -> int:
    return run(
        PY,
        "scripts/check_test_float_comparisons.py",
        "--against",
        param(params, "BASE", "origin/main"),
    )


@task(
    "lint.entrypoints",
    "app/cli vs scripts/ boundary; app/ must not read .dockerignore-excluded paths",
)
def _lint_entrypoints(_: dict[str, str]) -> int:
    return run(PY, "scripts/check_runtime_entrypoints.py")


@task("lint.modules", "Directory-scoped module placement/naming (.module-conventions.yml)")
def _lint_modules(_: dict[str, str]) -> int:
    return run(PY, "scripts/check_module_conventions.py", "--all")


@task(
    "lint.docs", "Agent docs describe the real app: no stale placeholders, every package documented"
)
def _lint_docs(_: dict[str, str]) -> int:
    return run(PY, "scripts/check_docs_freshness.py")


@task("checks", "Every whole-tree static check CI runs (no DB, no diff base needed)")
def _checks(params: dict[str, str]) -> int:
    for name in (
        "lint",
        "typecheck",
        "lint.imports",
        "lint.complexity",
        "lint.entrypoints",
        "lint.modules",
        "lint.docs",
    ):
        TASKS[name].fn(params)
    return run_all(
        (PY, "scripts/check_route_conventions.py", "--all"),
        (PY, "scripts/check_request_transaction_policy.py", "--all"),
        (PY, "scripts/check_unscoped_delete.py", "--all"),
        (PY, "scripts/check_empty_method_stubs.py", "--all"),
        (PY, "scripts/check_migration_enum_case.py", "--all"),
    )


@task("checks.diff", "Every diff-scoped guard against BASE (default origin/main)")
def _checks_diff(params: dict[str, str]) -> int:
    for name in (
        "lint.filesize",
        "lint.migrations",
        "lint.duplication",
        "lint.test-docstrings",
        "lint.test-float",
    ):
        TASKS[name].fn(params)
    return 0


# ---------------------------------------------------------------- tests


@task("test", "Fast default: unit tests only")
def _test(params: dict[str, str]) -> int:
    return TASKS["test.unit"].fn(params)


@task("test.unit", "Unit tests (no database)")
def _test_unit(_: dict[str, str]) -> int:
    return run(PY, "-m", "pytest", "tests/unit", "-q")


@task("test.integration", "Integration tests (needs TEST_DATABASE_URL + PYTEST_ALLOW_DB=1 in .env)")
def _test_integration(_: dict[str, str]) -> int:
    return run(PY, "-m", "pytest", "tests/integration", "-q")


@task("test.e2e", "Browser tests against a running server (TEST_BASE_URL, default localhost:8000)")
def _test_e2e(_: dict[str, str]) -> int:
    return run(PY, "-m", "pytest", "tests/e2e", "-q", "-m", "e2e")


@task("coverage", "Unit + integration with terminal + HTML report (TESTS)")
def _coverage(params: dict[str, str]) -> int:
    tests = param(params, "TESTS", "tests/unit tests/integration").split()
    code = run(
        PY,
        "-m",
        "pytest",
        *tests,
        "-q",
        "--cov=app",
        "--cov-report=term-missing",
        "--cov-report=html",
    )
    print("HTML report: open htmlcov/index.html")
    return code


@task(
    "coverage.diff",
    "Patch-coverage gate: >=80% of changed app/ lines covered (BASE, DIFF_COVER_FAIL_UNDER)",
)
def _coverage_diff(params: dict[str, str]) -> int:
    tests = param(params, "TESTS", "tests/unit tests/integration").split()
    run(PY, "-m", "pytest", *tests, "-q", "--cov=app", "--cov-report=xml")
    return run(
        tool("diff-cover"),
        "coverage.xml",
        f"--compare-branch={param(params, 'BASE', 'origin/main')}",
        f"--fail-under={param(params, 'DIFF_COVER_FAIL_UNDER', '80')}",
    )


@task("perf", "Per-route query-count budgets (tests/integration/perf/budgets.py)")
def _perf(_: dict[str, str]) -> int:
    return run(PY, "-m", "pytest", "tests/integration/perf", "-q")


@task("playwright.install", "Install Chromium for e2e tests (once)")
def _playwright_install(_: dict[str, str]) -> int:
    return run(PY, "-m", "playwright", "install", "chromium")


# ---------------------------------------------------------------- migrations


@task("mig.revision", 'Autogenerate a revision: python tasks.py mig.revision m="add widgets"')
def _mig_revision(params: dict[str, str]) -> int:
    return run(
        tool("alembic"),
        "revision",
        "--autogenerate",
        "-m",
        _required(params, "m", '"describe the change"'),
    )


@task("mig.up", "alembic upgrade head")
def _mig_up(_: dict[str, str]) -> int:
    return run(tool("alembic"), "upgrade", "head")


@task("mig.down", "alembic downgrade -1")
def _mig_down(_: dict[str, str]) -> int:
    return run(tool("alembic"), "downgrade", "-1")


@task("mig.history", "alembic history")
def _mig_history(_: dict[str, str]) -> int:
    return run(tool("alembic"), "history", "--verbose")


@task("mig.current", "alembic current")
def _mig_current(_: dict[str, str]) -> int:
    return run(tool("alembic"), "current")


# ---------------------------------------------------------------- container / deploy


@task("docker.build", "Build the deployable image (IMAGE, default app-harness:local)")
def _docker_build(params: dict[str, str]) -> int:
    return run(
        "docker",
        "build",
        "--build-arg",
        f"GIT_SHA={git_sha()}",
        "-t",
        param(params, "IMAGE", "app-harness:local"),
        ".",
    )


@task("docker.run", "Run the built image locally on :8000 with .env")
def _docker_run(params: dict[str, str]) -> int:
    return run(
        "docker",
        "run",
        "--rm",
        "--env-file",
        ".env",
        "-e",
        "APP_ENV=stage",
        "-p",
        "8000:8000",
        param(params, "IMAGE", "app-harness:local"),
    )


@task("docker.up", "docker compose up (Postgres + app)")
def _docker_up(_: dict[str, str]) -> int:
    return run("docker", "compose", "up", "--build")


@task("docker.down", "docker compose down")
def _docker_down(_: dict[str, str]) -> int:
    return run("docker", "compose", "down")


@task("deploy.freshness", "How far behind BASE is the deployment at DEPLOY_URL? (reads /health)")
def _deploy_freshness(params: dict[str, str]) -> int:
    url = _required(params, "DEPLOY_URL", "https://your-app.example.com")
    return run(
        PY,
        "scripts/check_deploy_freshness.py",
        "--url",
        url,
        "--against",
        param(params, "BASE", "origin/main"),
    )


@task(
    "requirements",
    "Export a pinned requirements.txt from pyproject (Databricks Apps installs from it)",
)
def _requirements(_: dict[str, str]) -> int:
    uv = shutil.which("uv")
    if uv:
        code = run(uv, "pip", "compile", "pyproject.toml", "-o", "requirements.txt", "--quiet")
    else:
        result = subprocess.run(
            [PY, "-m", "pip", "freeze", "--exclude-editable"],
            capture_output=True,
            text=True,
            cwd=REPO,
            check=True,
        )
        (REPO / "requirements.txt").write_text(result.stdout, encoding="utf-8")
        code = 0
    lines = len((REPO / "requirements.txt").read_text(encoding="utf-8").splitlines())
    print(f"wrote requirements.txt ({lines} lines)")
    return code


# ---------------------------------------------------------------- evals


@task(
    "evals", "Run the LLM eval suite (SUITE, default core); real suites need provider credentials"
)
def _evals(params: dict[str, str]) -> int:
    return run(PY, "-m", "evals.runner", "--suite", param(params, "SUITE", "core"))


# ---------------------------------------------------------------- entrypoint


def parse(argv: list[str]) -> tuple[str, dict[str, str]]:
    """``<task> KEY=VALUE ... [positional...]`` -> (task, params)."""
    if not argv or argv[0] in {"-h", "--help"}:
        return "help", {}
    params: dict[str, str] = {}
    positional: list[str] = []
    for arg in argv[1:]:
        key, sep, value = arg.partition("=")
        if sep and key.replace("_", "").replace("-", "").isalnum():
            params[key] = value
        else:
            positional.append(arg)
    params["_positional"] = " ".join(positional)
    return argv[0], params


def main(argv: list[str] | None = None) -> int:
    name, params = parse(sys.argv[1:] if argv is None else argv)
    if name not in TASKS:
        print(f"unknown task '{name}'. Run `python tasks.py help`.", file=sys.stderr)
        return 2
    return TASKS[name].fn(params)


if __name__ == "__main__":
    raise SystemExit(main())
