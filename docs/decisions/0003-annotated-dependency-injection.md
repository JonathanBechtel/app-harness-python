# 0003 — `Annotated` dependency injection

**Status:** accepted · **Date:** 2026-09-07

## Context
The two predecessors disagreed: one enforced `db: AsyncSession = Depends(get_session)`, the other `Annotated[AsyncSession, Depends(get_session)]`. Mixed styles defeat the route-conventions guard and make the sanctioned spelling ambiguous.

## Decision
Routes receive sessions as `db: DbSession`, an `Annotated` alias in `app/api/deps.py`. Route-conventions rule R3 rejects bare `AsyncSession` parameters however they are aliased.

## Consequences
One spelling, greppable, type-checker friendly. Other dependencies follow the same `Annotated[...]` shape.
