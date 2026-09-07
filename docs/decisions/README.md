# Architecture Decision Records

One file per decision, numbered, written when the decision is made. Accepted records are immutable: to change course, write a new record that supersedes the old one and link both ways. Use `template.md`.

| # | Decision | Status |
|---|---|---|
| 0001 | Single source of agent instructions (CLAUDE.md; AGENTS.md/GEMINI.md are pointers) | accepted |
| 0002 | Postgres + asyncpg + SQLModel as the persistence stack | accepted |
| 0003 | `Annotated` dependency injection (`DbSession`) in FastAPI | accepted |
| 0004 | The container image is the deploy artifact; targets adapt to it | accepted |
| 0005 | `models/` are ORM tables, `schemas/` are Pydantic contracts | accepted |
| 0006 | One repo, one stack, every use case (optional web and AI layers stay present) | accepted |
