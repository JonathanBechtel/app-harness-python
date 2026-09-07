# app/ — the shipped package

This is the only code that ships in the image (`.dockerignore` excludes everything else). Layout is by responsibility, and import-linter (`pyproject.toml [tool.importlinter]`) enforces the arrows:

```
api/ web/ cli/  ──►  services/  ──►  repositories/  ──►  models/
                        │
      schemas/ (edge contracts)   domain/ (pure)   ai/ (LLM plumbing)
      observability/ (ops plane, imports nothing)   utils/ (stateless)
```

| Package | Holds | Must not |
|---|---|---|
| `api/` | Routers, dependencies. Thin: wire request → service → response. | Import repositories; call commit/rollback. |
| `web/` | Optional Jinja page routes + `templating.py`. Same rules as `api/`. | Import repositories. |
| `services/` | Business logic, sequencing, **transaction boundaries** (`async with db.begin():`). | Import `api`/`web`/`cli`. |
| `repositories/` | Row-level reads/writes taking a session. | Commit, rollback, orchestrate. |
| `models/` | SQLModel tables — the canonical schema Alembic reads. | Import anything above it. |
| `schemas/` | Pydantic request/response contracts at the edge. | Be used as ORM tables. |
| `domain/` | ORM-free value objects and pure rules. | Import persistence, services, or the edge. |
| `ai/` | Role→model registry, client seam, versioned prompts. | Hard-code a model id (see `tests/unit/test_model_centralization.py`). |
| `cli/` | Runtime jobs run *inside the image* as `python -m app.cli.<job>`. | Import or read from `scripts/`, `tests/`, `docs/`, `deploy/`, `evals/`. |
| `observability/` | Correlation context, formatters, scrubbing. | Import any other app package. |
| `utils/` | Stateless helpers (`<domain>_utils.py`), DB engine, runtime guards. | Hold business rules. |
| `data/` | Runtime assets the package reads (declared in `pyproject` package-data). | Hold operator-only data (that goes in `scripts/data/`). |

Each subpackage has its own `CLAUDE.md` with the conventions that apply there. **When you add a package, add its `CLAUDE.md` and a row above** — `scripts/check_docs_freshness.py` fails the build otherwise.
