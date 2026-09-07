# Adding a guard

Use when a bug, review finding, or convention keeps being broken by hand and the class of failure is mechanisable.

1. **Write the failure down.** One paragraph: what happened, why review missed it, what would have caught it. This becomes the script docstring. If you cannot name a failure, do not add the rule.
2. **Choose the tier.** Syntactic/local → AST checker. Cross-frame/semantic → runtime guard (dev/test raise, prod warn). Layering → import-linter contract in `pyproject.toml`. A hand-maintained list mirroring a structure the code knows → reflective unit test (the code supplies the universe, the test asserts the list covers it, stale entries fail too).
3. **Implement** in `scripts/check_<rule>.py`:
   - path-taking → `run_cli(argv, CheckSpec(...))`; `check_all()` must raise if the scope matches nothing;
   - whole-tree → own argparse, `report(...)`, refuse empty scans;
   - line-scoped → `diff_scoped_cli(...)` so untouched lines never fail.
   - Resolve names via `_astutil.module_aliases/resolve`; support `# discipline: <rule> <reason>` via `_discipline`; scope string scans to real sinks so prose that *discusses* the hazard passes (`_astutil.docstring_node_ids`).
4. **Prove it fires.** `tests/unit/test_check_<rule>.py`: a seeded violation is reported; compliant code passes; the waiver works only with a reason; `test_repo_is_clean` asserts the tree passes today. Watch the test fail before the guard exists.
5. **Wire all three** with identical scope: `tasks.py` task (+ add to `checks` if whole-tree), `.pre-commit-config.yaml` hook, `ci.yml` step (or rely on `make checks`). `tests/unit/test_guard_wiring.py` checks presence.
6. **Catalog it** in `programmatic-code-discipline.md` (docs-freshness D3 fails otherwise) and mention the convention in the relevant package `CLAUDE.md`.
7. **Baseline, don't block.** If the tree has existing violations, ship a shrink-only allowlist or diff-scope the rule. A stale allowlist entry must fail, or the baseline silently claims more debt than exists.
