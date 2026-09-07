#!/usr/bin/env python3
"""Provision a clean machine to CI parity, on Windows, macOS, or Linux.

Creates a virtualenv, installs the project with dev extras, starts (or adopts)
a local Postgres on :5439 via Docker, writes a credential-free ``.env``,
applies migrations, installs pre-commit hooks, and runs the unit-test smoke
check. Idempotent; never overwrites an existing ``.env``. Exits non-zero if
the smoke check fails, because an automated caller cannot otherwise tell a
usable environment from one whose own verification failed.

    python scripts/bootstrap_env.py                 # everything
    python scripts/bootstrap_env.py --skip-db       # toolchain only
    python scripts/bootstrap_env.py --with-browsers # also install Chromium
    python scripts/bootstrap_env.py --no-venv       # install into the current interpreter
"""

from __future__ import annotations

import argparse
import os
import secrets
import shutil
import socket
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
IS_WINDOWS = os.name == "nt"
PG_PORT = int(os.environ.get("BOOTSTRAP_PG_PORT", "5439"))
PG_CONTAINER = os.environ.get("BOOTSTRAP_PG_CONTAINER", "app-harness-pg")
PG_IMAGE = "postgres:16"
PG_BASE = f"postgresql+asyncpg://postgres:postgres@localhost:{PG_PORT}"


def log(msg: str) -> None:
    print(f"\n==> {msg}", flush=True)


def warn(msg: str) -> None:
    print(f"warning: {msg}", file=sys.stderr, flush=True)


def die(msg: str) -> None:
    print(f"error: {msg}", file=sys.stderr, flush=True)
    raise SystemExit(1)


def run(
    *cmd: str, check: bool = True, capture: bool = False, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(cmd),
        cwd=REPO,
        check=check,
        text=True,
        capture_output=capture,
        env={**os.environ, **(env or {})},
    )


def venv_python(venv: Path) -> Path:
    return venv / ("Scripts/python.exe" if IS_WINDOWS else "bin/python")


def ensure_interpreter(use_venv: bool) -> Path:
    """Return the interpreter to install into, creating .venv unless told otherwise."""
    if sys.version_info < (3, 12):  # noqa: UP036 -- bootstrap may be launched by an older system python
        die(f"Python >= 3.12 required; running {sys.version.split()[0]}")
    active = os.environ.get("VIRTUAL_ENV") or os.environ.get("CONDA_PREFIX")
    if not use_venv or active:
        print(f"using the current interpreter: {sys.executable}")
        return Path(sys.executable)
    venv = REPO / ".venv"
    if not venv_python(venv).exists():
        log("Creating .venv")
        run(sys.executable, "-m", "venv", str(venv))
    print(f"using {venv_python(venv)}")
    return venv_python(venv)


def install(py: Path) -> None:
    log("Installing dependencies (pip install -e .[dev])")
    uv = shutil.which("uv")
    if uv:
        run(uv, "pip", "install", "--python", str(py), "-e", ".[dev]", "--quiet")
    else:
        run(str(py), "-m", "pip", "install", "--upgrade", "pip", "--quiet")
        run(str(py), "-m", "pip", "install", "-e", ".[dev]", "--quiet")
    print("installed")


def port_open(port: int) -> bool:
    with socket.socket() as s:
        s.settimeout(1)
        return s.connect_ex(("127.0.0.1", port)) == 0


def docker_available() -> bool:
    return (
        bool(shutil.which("docker"))
        and run("docker", "info", check=False, capture=True).returncode == 0
    )


def start_postgres() -> None:
    log(f"Postgres on :{PG_PORT}")
    if not docker_available():
        warn("Docker is unavailable; looking for a Postgres already on the port")
        return
    names = run("docker", "ps", "-a", "--format", "{{.Names}}", capture=True).stdout.split()
    if PG_CONTAINER in names:
        run("docker", "start", PG_CONTAINER, capture=True)
        print(f"started existing container {PG_CONTAINER}")
    elif port_open(PG_PORT):
        print(f"adopting the Postgres already listening on :{PG_PORT}")
    else:
        run(
            "docker",
            "run",
            "-d",
            "--name",
            PG_CONTAINER,
            "-e",
            "POSTGRES_USER=postgres",
            "-e",
            "POSTGRES_PASSWORD=postgres",
            "-e",
            "POSTGRES_DB=app",
            "-p",
            f"{PG_PORT}:5432",
            PG_IMAGE,
            capture=True,
        )
        print(f"created container {PG_CONTAINER}")


DB_SETUP = r"""
import sys, time
import psycopg
port = int(sys.argv[1])
dsn = f"postgresql://postgres:postgres@localhost:{port}/postgres"
deadline = time.time() + 60
conn = None
while time.time() < deadline:
    try:
        conn = psycopg.connect(dsn, autocommit=True, connect_timeout=3); break
    except psycopg.OperationalError:
        time.sleep(1)
if conn is None:
    print(f"no Postgres answered on :{port} within 60s", file=sys.stderr); sys.exit(1)
with conn.cursor() as cur:
    for db in ("app", "app_test"):
        cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (db,))
        if cur.fetchone() is None:
            cur.execute(f'CREATE DATABASE "{db}"'); print(f"created database {db}")
        else:
            print(f"database {db} already present")
conn.close()
"""


def create_databases(py: Path) -> bool:
    """Create app + app_test through psycopg (installed in the env); True on success."""
    return run(str(py), "-c", DB_SETUP, str(PG_PORT), check=False).returncode == 0


def write_env(app_url: str, test_url: str, db_ready: bool) -> None:
    log("Environment file")
    env_path = REPO / ".env"
    if env_path.exists():
        print(".env already exists -- left untouched")
        return
    env_path.write_text(
        "# Generated by scripts/bootstrap_env.py -- sandbox-safe, no real credentials.\n"
        "APP_ENV=dev\nDEBUG=1\nLOG_LEVEL=INFO\n"
        f"SECRET_KEY={secrets.token_urlsafe(32)}\n"
        f"DATABASE_URL={app_url}\nTEST_DATABASE_URL={test_url}\n"
        f"PYTEST_ALLOW_DB=1\nPYTEST_REQUIRE_DB={int(db_ready)}\nANTHROPIC_API_KEY=\n",
        encoding="utf-8",
    )
    print("wrote .env")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--skip-db", action="store_true")
    parser.add_argument("--with-browsers", action="store_true")
    parser.add_argument("--no-venv", action="store_true")
    args = parser.parse_args(argv)

    log("Python toolchain")
    py = ensure_interpreter(use_venv=not args.no_venv)
    install(py)

    db_ready = False
    app_url, test_url = f"{PG_BASE}/app", f"{PG_BASE}/app_test"
    if args.skip_db:
        log("Skipping database (--skip-db)")
    elif os.environ.get("TEST_DATABASE_URL"):
        log("Using the TEST_DATABASE_URL already set in this environment")
        test_url = os.environ["TEST_DATABASE_URL"]
        app_url = os.environ.get("DATABASE_URL", test_url)
        db_ready = True
    else:
        start_postgres()
        db_ready = create_databases(py)
        if not db_ready:
            warn(
                "No Postgres provisioned. Unit tests and static checks still work; integration tests need TEST_DATABASE_URL."
            )

    write_env(app_url, test_url, db_ready)

    if db_ready:
        log("Applying migrations (alembic upgrade head)")
        run(str(py), "-m", "alembic", "upgrade", "head")

    log("Installing pre-commit hooks")
    run(str(py), "-m", "pre_commit", "install", "--install-hooks", capture=True)
    print("hooks installed")

    if args.with_browsers:
        log("Installing Playwright Chromium")
        if (
            run(
                str(py), "-m", "playwright", "install", "--with-deps", "chromium", check=False
            ).returncode
            != 0
        ):
            run(str(py), "-m", "playwright", "install", "chromium")

    log("Smoke check (unit tests)")
    ok = (
        run(
            str(py),
            "-m",
            "pytest",
            "tests/unit",
            "-q",
            "-x",
            "--no-header",
            "-p",
            "no:warnings",
            check=False,
        ).returncode
        == 0
    )
    if not ok:
        die("environment installed but the smoke check failed")

    print("\n==> Bootstrap complete\n")
    activate = r".venv\Scripts\activate" if IS_WINDOWS else "source .venv/bin/activate"
    print(
        f"Activate:   {activate}\n"
        "Working now:\n"
        "  python tasks.py checks            every static check CI runs   (or: make checks)\n"
        "  python tasks.py test              unit tests\n"
        "  python tasks.py test.integration  (if a database was provisioned)\n"
        "  python tasks.py dev               server on :8000\n\n"
        "Needs credentials or a human: evals (provider keys), test.e2e (a running server +\n"
        "--with-browsers), deploys (Azure / Databricks auth)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
