# app-harness-python

A starting point for internal applications: a FastAPI service skeleton with the engineering guardrails already wired in. **It contains no product logic.** It contains everything that lets a new project start safely on day one and stay that way:

- **Guardrails that run in three places** (pre-commit, `make`, CI) and cannot drift apart: lint, types, import-layer contracts, complexity and file-size ratchets, migration lock-safety, duplicate-code gate, route conventions, transaction policy, delete-scope ban, test hygiene, and a docs-freshness check.
- **A test harness** with a real-Postgres integration tier (per-session schema isolation, explicit opt-in, no silent skips), unit tests that physically cannot touch a database, query-count budgets, browser smoke tests, and meta-tests proving every guard fires.
- **One deploy artifact** (the container image) with adapters for Azure Container Apps and Databricks Apps, health probes, release identity, and a drift monitor.
- **Agent documentation** that tells any AI what this repo is and how to work in it, plus mechanical pressure to keep those docs describing the real app as it grows.
- **LLM plumbing** without product logic: role→model routing, a mockable client seam, versioned prompts, and an eval harness.

This is the Python sibling of [`app-harness-typescript`](https://github.com/JonathanBechtel/app-harness-typescript) (Fastify). The two keep functional and structural parity: the same guards, the same layout, the same deploy contract, each in its own ecosystem's idioms.

## Start a project

```bash
# 1. Create a repo from this template, clone it, then (any OS):
python scripts/bootstrap_env.py     # venv, deps, local Postgres on :5439, .env, hooks, smoke test
python tasks.py dev                 # http://localhost:8000/health   (or: make dev)
# 2. Follow docs/guides/new-project-checklist.md (rename, describe the app, pick deploy targets).
```

Everything an engineer or agent needs is in [`CLAUDE.md`](CLAUDE.md). `python tasks.py help` (or `make help`) lists every task.

**Windows, macOS, Linux.** Requirements are Python 3.12 and Docker Desktop. Every task is defined once in `tasks.py` and runs without a shell; the `Makefile` is a thin shim for people who like `make`. Native Windows (PowerShell) works as-is; WSL2 also works. Line endings are normalised to LF by `.gitattributes`.

## Layout

```
app/            shipped package (api, web, services, repositories, models, schemas, domain, ai, cli, observability, utils)
scripts/        operator tooling and the guard scripts (never shipped)
tests/          unit / integration / e2e (+ perf budgets, guard meta-tests)
evals/          LLM quality benchmarks (on demand)
docs/           architecture, guides, decisions (ADRs), plans, runbooks
deploy/         target adapters: Azure Container Apps, Databricks Apps
.github/        CI, image build, deploys, drift monitor
.claude/        agent settings, Stop hook (pre-commit gate), skills, review agent
```

## Why so many guards?

Every rule here descends from a real failure in a predecessor codebase, is enforced mechanically rather than by review, ships with an escape hatch that requires a written reason, and is baselined so it never blocks unrelated work. The reasoning is in [`docs/guides/programmatic-code-discipline.md`](docs/guides/programmatic-code-discipline.md).
