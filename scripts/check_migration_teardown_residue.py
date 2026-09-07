"""Assert ``alembic downgrade base`` left the public schema genuinely empty.

"Exits 0" and "left nothing behind" are different claims: revisions that drop
tables but not the enum types their columns used leave orphans that only
surface later as a confusing DuplicateObjectError. Run this right after a
downgrade against a database that started empty.

Usage: ``DATABASE_URL=postgresql+asyncpg://... python scripts/check_migration_teardown_residue.py``
"""

from __future__ import annotations

import os
import sys

import psycopg


def main() -> int:
    url = os.environ.get("DATABASE_URL")
    if not url:
        print("DATABASE_URL is required", file=sys.stderr)
        return 2
    conn = psycopg.connect(url.replace("+asyncpg", "").replace("+psycopg", ""))
    findings: list[str] = []
    with conn, conn.cursor() as cur:
        cur.execute(
            "SELECT tablename FROM pg_tables WHERE schemaname = 'public' AND tablename <> 'alembic_version'"
        )
        findings += [f"table left behind: {row[0]}" for row in cur.fetchall()]
        cur.execute(
            "SELECT t.typname FROM pg_type t JOIN pg_namespace n ON n.oid = t.typnamespace "
            "WHERE n.nspname = 'public' AND t.typtype = 'e'"
        )
        findings += [f"enum type left behind: {row[0]}" for row in cur.fetchall()]
        cur.execute("SELECT viewname FROM pg_views WHERE schemaname = 'public'")
        findings += [f"view left behind: {row[0]}" for row in cur.fetchall()]
    if findings:
        print("migration teardown residue:\n  " + "\n  ".join(findings), file=sys.stderr)
        return 1
    print("migration teardown: schema is clean")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
