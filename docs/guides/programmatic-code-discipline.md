# Programmatic code discipline

**Purpose:** encode past failures as automated enforcement so a build-in-a-hurry cannot repeat them. Lint is a floor, not a ceiling: it stops known failure modes from silently recurring under deadline pressure; it does not produce good design.

## The governing rule

> **Every rule traces to a specific past failure.** Rules without a failure behind them become noise, and noise trains people to bypass the whole system. When adding a rule, name the incident in the script's docstring.

**Every rule ships with:** the failure it descends from (docstring), an escape hatch requiring a written reason (`# discipline: <rule> <reason>`; a bare marker is not a waiver), and a baseline or diff-scoping so it never blocks unrelated work.

**Every rule runs in three places** — `tasks.py`, `.pre-commit-config.yaml`, `.github/workflows/ci.yml` — with identical scope, so nothing passes locally and fails in CI or the reverse. Pre-commit is bypassable; CI is the enforcing copy. `tests/unit/test_guard_wiring.py` asserts the three agree.

**Every rule has a test proving it fires.** A guardrail nobody has watched fail is an assumption (`tests/unit/test_check_*.py`).

**Every rule refuses to pass on an empty scan.** "Checked nothing" must never print OK (`scripts/_check_runner.py`).

**Every rule resolves aliases.** `from sqlalchemy import delete as sa_delete` must not switch a guard off (`scripts/_astutil.py`).

## Three tiers

| Tier | Mechanism | Catches | Blind to |
|---|---|---|---|
| 1 | AST checkers (`scripts/check_*.py`) | syntactic, local patterns | anything across call frames |
| 2 | Runtime guards (`app/utils/network_guard.py`) | cross-frame, semantic violations at any depth | paths no test or traffic exercises |
| 3 | Structural contracts (import-linter, reflective tests, budgets) | layering drift, stale hand-maintained lists, cost creep | duplication that needs no import |

AST is not enough on its own: the worst transaction bug in the source material was an HTTP call four frames below the `db.begin()` block. Tier 2 exists for that.

## Guard catalog

Whole-tree guards run on every push; diff-scoped ones compare against the PR base so existing code is never retrofitted wholesale.

| Guard | Scope | Failure it descends from |
|---|---|---|
| `ruff` (lint+format), `mypy app` | whole tree | type drift, unreadable diffs |
| `import-linter` contracts (`pyproject.toml`) | whole tree | a "generic" framework secretly coupled to one source; routers querying tables directly |
| `check_complexity_ratchet.py` + `complexity-baseline.json` | whole tree | per-file-ignores hiding growth inside already-complex files |
| `check_file_size_ratchet.py` | diff | 5,000-line services; 35,000-line merges beyond a reviewable unit |
| `check_route_conventions.py` | path | untyped endpoints, implicit 200 on writes, sessions built inline, templates without `request` |
| `check_request_transaction_policy.py` | path | commits scattered through services; partial writes on error |
| `check_unscoped_delete.py` | path | a rebuild that wiped tables every run, destroying history (north-star P2) |
| `check_empty_method_stubs.py` | path | overrides that silently swallowed behaviour |
| `check_migration_enum_case.py` | path | enum migrations that rejected every ORM insert on the live DB |
| `check_migration_safety.py` | diff | a non-concurrent index build that stalled a deploy and 500'd public routes for 96 minutes |
| `check_migration_teardown_residue.py` | CI round-trip | downgrades that "passed" but left orphaned enum types |
| `check_duplicate_code.py` | diff (3% of changed lines) | decompositions that copied helpers into both halves; AI-assisted duplication |
| `check_test_docstrings.py` | diff (line) | undocumented tests nobody could interpret when they failed |
| `check_test_float_comparisons.py` | diff (line) | flaky float equality in golden-number tests |
| `check_runtime_entrypoints.py` | whole tree | a shipped module that read from `scripts/` and broke only in the container |
| `check_module_conventions.py` + `.module-conventions.yml` | path | placement/naming drift in directories that had been standardised |
| `check_docs_freshness.py` | whole tree | a project whose CLAUDE.md still described the template six months in |
| `check_deploy_freshness.py` (scheduled) | observation | production ran a 3.5-day-old image through an incident whose fix was merged |
| `network_guard.py` (runtime) | any depth | HTTP calls inside open transactions holding locks across round-trips |
| `test_settings_documented.py`, `test_model_centralization.py`, `test_route_table.py` | reflective | undocumented settings, unscrubbed secrets, model ids in six places, routes silently disappearing |
| `tests/integration/perf/budgets.py` | budget | a 25-query serial waterfall of sub-3ms queries |

## What should NOT be a lint rule

- Freshness semantics — encode in a value type, not a regex.
- "Is this the right abstraction?" — judgment; that is what review questions in `docs/architecture/north-star.md` are for.
- File cohesion — line count is a proxy; a 400-line file doing three things is worse than a 700-line cohesive one. The ratchet buys pressure, not wisdom.
- Architectural intent — no checker notices a framework has one instance.

## Adding a rule

See `docs/guides/adding-a-guard.md` and the `/add-guard` skill. Two rules that are respected beat eight that get waived.
