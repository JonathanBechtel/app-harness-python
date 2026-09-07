---
name: add-guard
description: Turn a bug, review finding, or convention into a permanent mechanical guard (AST checker, import contract, reflective test, or runtime guard) wired into Makefile, pre-commit, and CI with a test proving it fires. Use right after fixing a regression or when a rule keeps being broken by hand.
allowed-tools: Bash, Read, Write, Edit, Grep, Glob
---

# Add a guard

Read `docs/guides/adding-a-guard.md` first. Then:

1. **Name the failure.** Write the incident (what happened, why review missed it) — it becomes the script docstring. No failure, no rule.
2. **Pick the tier** (`docs/guides/programmatic-code-discipline.md`): AST checker for syntactic/local patterns; import-linter contract for layering; reflective unit test for hand-maintained lists; runtime guard for cross-frame behaviour.
3. **Write it** in `scripts/check_<rule>.py` using `_check_runner.py` (path-taking → `run_cli`; whole-tree → own argv + `report`; line-scoped → `diff_scoped_cli`). Resolve aliases with `_astutil`. Support `# discipline: <rule> <reason>` via `_discipline` unless there is a reason not to. Refuse to pass on an empty scan.
4. **Prove it fires.** `tests/unit/test_check_<rule>.py`: seed the original violation into a temp file and assert the checker reports it; assert a compliant sample passes; assert the repo is currently clean.
5. **Wire all three**: `tasks.py` task, `.pre-commit-config.yaml` hook (mirroring CI's scope exactly), `.github/workflows/ci.yml` step. `tests/unit/test_guard_wiring.py` asserts they agree.
6. **Catalog it** in `docs/guides/programmatic-code-discipline.md` (the docs-freshness check fails otherwise).
