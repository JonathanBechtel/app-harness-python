# Migrations

`app/models/` is the canonical schema; Alembic inspects it. See CLAUDE.md
"Migration Workflow" for the rules and `make mig.*` for the commands.

Every revision must round-trip: `make lint.migrations.roundtrip ROUNDTRIP_DATABASE_URL=...`
runs upgrade → downgrade → asserts the schema is genuinely empty → upgrade. CI runs
the same check on an ephemeral Postgres for every PR.
