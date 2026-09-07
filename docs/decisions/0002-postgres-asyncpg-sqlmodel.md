# 0002 — Postgres + asyncpg + SQLModel

**Status:** accepted · **Date:** 2026-09-07

## Context
One predecessor ran MySQL, the other Postgres. The harness pieces worth keeping (concurrent index migrations, schema-per-session test isolation, enum-type teardown checks, advisory locks) are Postgres-shaped, and both deploy targets (Azure Database for PostgreSQL, Databricks Lakebase) offer managed Postgres.

## Decision
Postgres via `postgresql+asyncpg://`, SQLModel tables as the canonical schema, Alembic migrations with `lock_timeout` and one transaction per revision.

## Consequences
Migration-safety and teardown guards are exact rather than approximate. Swapping databases is possible but means rewriting those guards; record it as a superseding ADR.
