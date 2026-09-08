# Agent instructions — read this first

This file is the single source of project instructions for every AI agent and every engineer. `AGENTS.md` and `GEMINI.md` point here. Per-package rules live in each package's own `CLAUDE.md`; read the nearest one before editing a file.

## What this repository is

<!-- template:placeholder -->
> **Template placeholder — replace with the truth about this application.** This repository was created from the *app-harness* template: a FastAPI service skeleton carrying the organisation's engineering guardrails, test harness, deploy pipeline, and agent documentation. Until this section is rewritten, the app is the template. Describe: the product and its users, the domain vocabulary, the external systems, the deploy targets in use, and what "done" means for this project's UI (if it has one). Then delete this blockquote. `make lint.docs` fails while placeholders remain once real code exists.

**Purpose:** _one paragraph._

**Users:** _who, and what they need from it._

**Not in scope:** _what this app deliberately does not do._

## Your obligations to the next agent

The next agent will read this file to learn how the app works. Keep it true:

1. **Docs change with the code, in the same PR.** New package → its `CLAUDE.md` and a row in `app/CLAUDE.md`. New route, job, setting, or integration → the relevant section here and `.env.example`. New convention → the package `CLAUDE.md` and, if mechanisable, a guard (`/add-guard`).
2. **Record decisions** in `docs/decisions/` when you choose a library, draw a boundary, or adopt a pattern. Future you needs the *why*.
3. **Run `make lint.docs`** before finishing; it fails on undocumented packages, stale template placeholders, and references to make targets that do not exist. The `/update-docs` skill walks the full procedure.
4. **Do not paper over a failing guard.** Every guard has a `# discipline: <rule> <reason>` escape hatch; use it with a real reason visible in review, never `--no-verify`.

## Definition of Done

No task is complete until these pass. Run them proactively; do not ask whether to. Every `make <task>` below is equivalently `python tasks.py <task>` (Windows without make).

1. `make checks` — ruff, mypy over `app/`, import contracts, complexity ratchet, entrypoint boundary, module conventions, docs freshness, and the route/transaction/delete/stub/enum guards.
2. `make lint.filesize lint.migrations lint.duplication lint.test-docstrings lint.test-float` — diff-scoped guards against `origin/main` (CI enforces them against the PR base).
3. `make test.unit`; `make test.integration` when a database is available; `make coverage.diff` (≥80% of changed `app/` lines covered — CI fails below it).
4. UI changes: `make test.e2e` against `make dev`, then read the screenshots in `tests/e2e/screenshots/`.
5. Prompt or model changes: `make evals` and paste the score into the PR.

Pre-commit only sees staged files; CI checks the whole tree, so run the tasks, not just the hooks. If an environment cannot run a step (no database, no browser, no credentials), say so explicitly rather than reporting it as passed. `python scripts/bootstrap_env.py` provisions a clean machine to CI parity.

## Layout and boundaries

```
app/       shipped package — see app/CLAUDE.md for the layer table and import rules
scripts/   operator tooling + guard scripts; never shipped, never imported by app/
tests/     unit (no DB) · integration (Postgres) · e2e (browser) · perf budgets · guard meta-tests
evals/     LLM quality benchmarks, on demand
docs/      architecture · decisions · guides · plans · runbooks (docs/CLAUDE.md)
deploy/    target adapters; the image is the artifact (deploy/README.md)
```

**Executable code lives in two places.** If the deployed container runs it, it is `app/cli/<job>.py` invoked as `python -m app.cli.<job>`. If a human or CI runs it from a checkout, it is `scripts/`. Nothing under `app/` imports or reads from `scripts/`, `tests/`, `docs/`, `deploy/`, or `evals/` (they are absent from the image). Enforced by `scripts/check_runtime_entrypoints.py`.

## Tech stack

Python 3.12 · FastAPI · SQLModel/SQLAlchemy async · Postgres (asyncpg) · Alembic · Pydantic Settings · Jinja2 + vanilla CSS/JS (optional web layer, no build step) · pytest · ruff · mypy · import-linter · pre-commit · Docker. Cross-platform: tasks are Python (`tasks.py`), hooks are Python, no bash anywhere in the critical path; Windows, macOS and Linux are all first-class. The whole stack is present in every project, whether it uses the web layer or LLM features or neither. See `docs/decisions/`.

## Conventions

**Config.** All environment is read once in `app/config.py` (`settings`). Every field is documented in `.env.example`; every credential-shaped field is in the log-scrubbing list. Never `os.getenv` elsewhere for app config; never commit `.env`.

**API.** Thin routers; `db: DbSession` for injection; `response_model=`/`response_class=` on every route; explicit `status_code=` on writes; transactions via `async with db.begin():`. Details: `app/api/CLAUDE.md`.

**Services / repositories / models.** Services own logic and transaction boundaries, repositories own row access, models are the schema. Routers never import repositories. No network I/O inside an open transaction (runtime-guarded). `delete(Model)` always has a `.where(...)`.

**Naming.** `snake_case` functions, `PascalCase` classes, `UPPER_CASE` constants and enum members. Files: `<domain>_service.py`, `<domain>_repository.py`, `<domain>_utils.py`. Google-style docstrings on public functions; a one-line docstring on every test.

**Typing.** Validate at boundaries; strong types inside. Narrow with `isinstance`/early return, don't `cast`. No `Any` returns from typed functions. `mypy app` must be clean.

**Logging.** `logging.getLogger(__name__)`; bind context with `app.observability.bind`; never log a secret (scrubber is a backstop, not a licence). Errors that matter are `logger.exception`, not `print`.

**LLM features.** Call sites name a role; `app/ai/registry.py` resolves the model. Provider SDK code lives only in a `ModelClient` implementation; tests use `FakeModelClient`. Prompts are versioned modules. Guidance in `docs/guides/llm-features.md`.

**Frontend (when used).** Jinja templates extend `base.html`; shared primitives in `static/css/main.css`; page files kebab-case; BEM classes; no bundler. `app/web/CLAUDE.md`.

## Migration workflow

`app/models/` is canonical. `make mig.revision m="..."` autogenerates; review the diff. New tables: create exactly as defined; downgrade with explicit `op.drop_table()` and drop the enum types this revision created, after the tables. Existing tables: keep minimal `op.*` DDL, never drop/recreate. Index builds: `postgresql_concurrently=True` inside `op.get_context().autocommit_block()` in a dedicated idempotent revision. Every revision must round-trip (`make lint.migrations.roundtrip ROUNDTRIP_DATABASE_URL=<disposable>`); CI does this on every PR.

## Testing

TDD with integration tests as the primary signal: write the test that captures the behaviour, then implement. Unit tests (`tests/unit`) cannot open a database (a fixture forbids it). Integration tests (`tests/integration`) hit FastAPI via HTTPX and assert both HTTP responses and database state; they need `TEST_DATABASE_URL` + `PYTEST_ALLOW_DB=1`, and `PYTEST_REQUIRE_DB=1` makes a missing database a failure rather than a silent skip. Prefer factories over seed dumps; test behaviour (status codes, rows, payload shapes), not implementation. Query-count budgets live in `tests/integration/perf/budgets.py`; a failing budget means fix the N+1 or bump the number in the same diff, visibly. Details: `docs/guides/testing.md`.

## Git workflow

- Branches: `feature/`, `fix/`, `bug/`, `refactor/`, `enhancement/`, `docs/` + short kebab-case description. No agent names, dates, or ticket ids in the branch name.
- Commits: one logical unit each; conventional-commit subject under 72 chars; explain *why* in the body when the diff does not. Stage only that unit's files and run the smallest relevant verification first.
- **Authorship is the local git identity. Never add Co-Authored-By or any AI attribution.**
- Never `--no-verify`, never force-push shared branches, never amend pushed commits.
- Open PRs with the `/pr` skill; the PR template asks for verification and docs.

## Agent workflow

Idea → `/create-product-pitch` (optional for mechanical work) → tech spec in `docs/plans/` → `/create-qa-checklist` → `/create-project` (tickets) → `/orchestrate` (parallel agents) → `/ship`. Per-repo overrides for ticket generation and browser verification: `docs/plans/ai-orchestrator-ticket-spec.md`. The `verdict-qa` agent (`.claude/agents/`) is the fresh-eyes gate before declaring UI work done. Full description: `docs/guides/agent-workflow.md`.

**Planning vs. executing.** If asked to plan, outline, or assess, do that and stop; do not start changing files until asked. If asked to build, build it completely and run the Definition of Done without asking.

## Infrastructure

The container image is the artifact; targets are Azure Container Apps (image) and Databricks Apps (source, same commit). `/health` reports `release_sha`; `make deploy.freshness DEPLOY_URL=...` measures drift from `main`. Details and one-time setup: `deploy/README.md`. Secrets live in the platform's secret store, never in the repo or the image.

## Harness updates

This project receives template changes as a weekly `harness-sync` pull request (`.github/workflows/template-sync.yml`). Review it like a dependency bump and run the Definition of Done; `.templatesyncignore` lists the files this project owns. Procedure: `docs/guides/receiving-harness-updates.md`.

## Where the rules come from

Every guard traces to a named failure and ships with an escape hatch and a baseline: `docs/guides/programmatic-code-discipline.md`. Architectural principles: `docs/architecture/north-star.md`. Decisions: `docs/decisions/`.
