"""Alembic environment.

Every module under ``app/models`` is imported so autogenerate sees the whole
metadata: placing a new table module there is enough to make it discoverable.

Two lock-safety settings are load-bearing and guarded by
``scripts/check_migration_safety.py``:

* ``lock_timeout`` bounds lock *acquisition*: a migration that cannot get its
  lock fails fast and retryably instead of queueing ahead of production reads.
* ``transaction_per_migration=True`` bounds lock *lifetime*: each revision
  commits as it finishes rather than holding every ``ACCESS EXCLUSIVE`` lock
  until the last revision in the chain completes.
"""

from __future__ import annotations

import asyncio
import importlib
import os
import pkgutil
from logging.config import fileConfig
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import pool, text
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import SQLModel

from alembic import context
from app import models as models_pkg


def load_model_modules() -> None:
    """Import every module in app.models so SQLModel.metadata is complete."""
    prefix = models_pkg.__name__ + "."
    for _, name, _ in pkgutil.walk_packages(models_pkg.__path__, prefix):
        importlib.import_module(name)


load_model_modules()

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=False)

DB_URL = os.getenv("DATABASE_URL")
if not DB_URL:
    raise RuntimeError("DATABASE_URL is required for Alembic migrations")

MIGRATION_LOCK_TIMEOUT = os.getenv("ALEMBIC_LOCK_TIMEOUT", "10s")

config.set_main_option("sqlalchemy.url", DB_URL)
target_metadata = SQLModel.metadata


def run_migrations_offline() -> None:
    """Emit SQL without a live connection."""
    context.configure(
        url=DB_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Configure the sync context and run the chain, one transaction per revision."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
        transaction_per_migration=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Run migrations against the configured database."""
    engine = create_async_engine(DB_URL, poolclass=pool.NullPool, future=True)
    async with engine.connect() as connection:
        await connection.execute(
            text("SELECT set_config('lock_timeout', :timeout, false)"),
            {"timeout": MIGRATION_LOCK_TIMEOUT},
        )
        await connection.commit()
        await connection.run_sync(do_run_migrations)
    await engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
