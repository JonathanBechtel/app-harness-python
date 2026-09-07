# Testing

## Tiers

| Tier | Where | Needs | Runs in CI | Purpose |
|---|---|---|---|---|
| unit | `tests/unit` | nothing (a fixture forbids DB access) | yes | pure logic, guard meta-tests, reflective checks |
| integration | `tests/integration` | Postgres (`TEST_DATABASE_URL`, `PYTEST_ALLOW_DB=1`) | yes (service container) | routes via HTTPX + database state; the primary signal |
| perf | `tests/integration/perf` | Postgres | yes | per-route SQL statement budgets |
| e2e | `tests/e2e` (`-m e2e`) | a running server + Chromium | manual | a browser proves JS actually ran; screenshots for a human/agent to read |
| evals | `evals/` | provider credentials | manual | LLM answer quality; not a software test |

## The database gate

`tests/integration/conftest.py` requires explicit opt-in (`PYTEST_ALLOW_DB=1`) and a URL that is not the app database. With `PYTEST_REQUIRE_DB=1` (set by CI and by bootstrap) a missing URL is a **failure**, not a skip: an unprovisioned box exiting 0 with everything skipped is indistinguishable from green.

Isolation: one random schema per session, tables from SQLModel metadata, per-test rollback. Tests that need real commits (HTTP client, concurrency, durability) use `@pytest.mark.committed_db` or the `app_client` fixture and get truncated afterwards.

## Habits that hold up

- Write the integration test first; add unit tests for pure edge cases.
- Assert behaviour: status codes, rows created, payload shapes — not internals.
- Factories over seed dumps; small deterministic fixtures.
- One-line docstring on every test (enforced on changed tests); `pytest.approx` for floats (enforced).
- Never mock the database in an integration test; mock at the external boundary (HTTP client, provider `ModelClient`).
- A green suite with a skipped tier is not green. Report skips.

## Coverage

CI enforces ≥80% **patch** coverage on changed `app/` lines (`diff-cover`). Whole-project coverage is reported, not gated, so legacy debt never blocks a fix. `make coverage.diff` runs the same gate locally.

## Meta-tests

Every guard script has a test that seeds its original failure and asserts it fires. Whole-tree scans are excluded from coverage in CI (settrace makes them 5× slower and they measure no `app/` code).
