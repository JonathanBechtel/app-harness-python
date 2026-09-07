# North-star architecture

**Status:** principles. Short by design. Detail lives in the docs it maps to.

These principles were distilled from post-mortems of two predecessor systems. Edit them if this application's domain demands it, and record why in an ADR.

## The one idea

> Keep one durable canonical record. Everything users see is a thin, disposable projection computed *from* that record through *one* code path. Retain history by default.

Every significant defect in the retrospectives was a projection drifting from the record or from another projection: a metric disagreeing with the prose beside it, a freshness badge disagreeing with the data under it, the same statistic computed eight ways.

## Principles

**P1 — One canonical record; projections are thin readers.** Canonical facts (with provenance) are the durable record. Timelines, dashboards, caches, and reports are replaceable projections computed from them. One computation lives in one place; one fact is stored in one place; every projection carries a watermark saying which source state it reflects.

**P2 — Retain history by default.** Anything with analytical or evidentiary value is append-only and as-of-dated with a current-version pointer. "Wipe and recompute" destroys the time axis. Distinguish *evidence* (never destroyed) from *regenerable caches* (overwrite-in-place is fine, but stamp what they render). Mechanised by `scripts/check_unscoped_delete.py`.

**P3 — Sources are adapters, never stores.** Each external system is an adapter that translates its feed into canonical records on the shared backbone. No source keeps a parallel store; everything downstream is source-blind. Sibling adapters never import each other.

**P4 — Freshness means source currency, never process time.** "Last updated" reports how current the *data* is, not when a job last ran. Process-time fields belong on admin/ops surfaces only.

**P5 — Boring and conventional beats clever.** The backend is deliberately plain (FastAPI, SQLModel, Postgres, Jinja if a UI is needed) because it is optimised for AI-assisted change: predictable layout, mechanical rules, thin layers.

## Review questions for new work

1. Does this add a second place a fact is stored or computed? Why not read the canonical one?
2. Does anything get deleted or overwritten that someone might later need to explain a number?
3. Does a source-specific type leak past its adapter?
4. Does a user-facing surface show process time?
5. Could a guard (import contract, AST check, reflective test) enforce the boundary this design relies on? Add it in the same change.
