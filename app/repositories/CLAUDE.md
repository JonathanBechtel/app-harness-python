# app/repositories — row access

- Functions take a session and return ORM rows or plain values. No commit/rollback, no cross-repository orchestration.
- Files end in `_repository.py`. Routers never import this package (import-linter contract 3): scoped/authorized access is a service concern.
- `delete(Model)` must always carry a `.where(...)`; retain history by default (`scripts/check_unscoped_delete.py`).
