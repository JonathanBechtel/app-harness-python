# docs/ — documentation taxonomy

All project documentation lives here, by kind:

- `architecture/` — how the system is built: `overview.md` (this app), `north-star.md` (principles). Read before designing anything data-shaped.
- `decisions/` — Architecture Decision Records, numbered, immutable once accepted (supersede, do not edit). Template: `decisions/template.md`.
- `guides/` — how-to and conventions: discipline, testing, deployment, agent workflow, adding a guard, LLM features.
- `plans/` — active specs, pitches, QA checklists, and ticket specs; completed plans move to `plans/archive/`.
- `runbooks/` — operational procedures (incident response, backfills, credential rotation). Template: `runbooks/template.md`.
- `notes/` — dated debug sessions, audits, ad-hoc findings (`YYYY-MM-DD-slug.md`). Not authoritative.
- `product/` — PRDs, roadmaps, use cases.
- `research/` — external API discovery, organised by system.

Rules: a doc that describes code must change with the code, in the same PR. Never paste secrets or credentials into any doc. Prefer one accurate page over three partial ones.
