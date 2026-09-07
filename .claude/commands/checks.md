Run the full Definition of Done from CLAUDE.md and fix anything that fails:

1. `make checks` (ruff, mypy over app/, import-linter, complexity ratchet, entrypoint boundary, module conventions, docs freshness, route/transaction/delete/stub/enum guards)
2. `make lint.filesize lint.migrations lint.duplication lint.test-docstrings lint.test-float` (diff-scoped against origin/main)
3. `make test.unit`; `make test.integration` if a database is configured (`.env`), and `make coverage.diff` for the patch-coverage gate.
4. For UI changes: `make test.e2e` against `make dev` and read the screenshots.

Do not ask whether to run these; run them, fix failures, then report what ran and what was skipped (and why).
