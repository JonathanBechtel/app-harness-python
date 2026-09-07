# app/models — ORM tables

- SQLModel `table=True` classes, one module per aggregate. Mixins in `base.py`.
- This is the canonical schema. Alembic auto-imports every module here; after changing a table run `make mig.revision m="..."`, review the diff, and follow CLAUDE.md "Migration Workflow".
- Enum members are `UPPER_CASE` (the migration checker enforces it: SQLAlchemy persists member *names*).
