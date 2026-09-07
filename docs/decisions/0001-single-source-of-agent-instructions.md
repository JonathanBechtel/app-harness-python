# 0001 — Single source of agent instructions

**Status:** accepted · **Date:** 2026-09-07

## Context
Predecessor repos kept `CLAUDE.md` and `AGENTS.md` byte-identical by hand for Claude/Codex parity. Within one release cycle they drifted, on the hardest-won rules: one copy lost the architecture principles entirely, the two disagreed on how many corollaries a boundary rule had and whether an allowlist was empty. An invariant maintained by hand with no guard is not an invariant.

## Decision
`CLAUDE.md` is the only instruction file. `AGENTS.md` and `GEMINI.md` are pointers. Per-package `CLAUDE.md` files hold local conventions. Repo-local skills live in `.claude/skills/` and are exposed to other runtimes via symlinks in `.agents/skills/`.

## Consequences
Parity is structural: there is no second copy to drift. Runtimes that cannot follow a pointer get one sentence telling them where to look. `scripts/check_docs_freshness.py` keeps the single copy honest.
