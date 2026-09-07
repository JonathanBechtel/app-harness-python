# Orchestrator ticket spec (per-repo overrides)

Read by `/create-project` and by agents running browser verification. Universal skill behaviour applies unless overridden here.

## Repo defaults

| Setting | Value |
|---|---|
| Default agent model | `sonnet` for work tickets, `opus` for QA gates |
| Environment | `.venv` from `python scripts/bootstrap_env.py` |
| Test command | `make test.unit` / `make test.integration` / `pytest <path>` |
| Type check | `make typecheck` |
| All static checks | `make checks` |
| Dev server | `make dev` → `http://localhost:8000` |
| Screenshot harness | `make test.e2e` → `tests/e2e/screenshots/` |

## Test layout
`tests/unit` (no DB) · `tests/integration` (Postgres; `TEST_DATABASE_URL`, `PYTEST_ALLOW_DB=1`) · `tests/e2e` (opt-in `-m e2e`, live server). No `no_deps`/`with_deps` split.

## Verification flavours
- backend ticket: unit + integration
- UI ticket: integration + e2e + screenshots read by `verdict-qa`
- migration ticket: integration + `make lint.migrations` + round-trip in CI

## Browser verification
Use the Playwright MCP (`.mcp.json`) against `make dev`. Never type credentials into a form via a tool call; if the app has auth, add a cookie-minting script under `scripts/` and document it here.

## Databases during orchestration
Each agent worktree runs `python scripts/bootstrap_env.py --skip-db` and points `TEST_DATABASE_URL` at its own database on the shared local Postgres (create one per worktree; the suite isolates by schema anyway).
