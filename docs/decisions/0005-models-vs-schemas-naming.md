# 0005 — `models/` are ORM tables, `schemas/` are Pydantic contracts

**Status:** accepted · **Date:** 2026-09-07

## Context
The predecessors used the two words in opposite senses. Either convention works; having both in one organisation does not.

## Decision
`app/models/` = SQLModel tables (the schema Alembic reads). `app/schemas/` = Pydantic request/response models. Repositories return models; services map to schemas at the edge.

## Consequences
Matches the more common ecosystem usage. Alembic env and test fixtures import `app.models`.
