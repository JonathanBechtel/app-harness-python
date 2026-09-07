# app/api — HTTP edge

- One module per resource under `routes/`; every router variable is named `router`; register it in `app/main.py`.
- Routes are thin: parse → call a service → shape the response. No queries, no business rules.
- Dependency injection uses `Annotated`: `db: DbSession` (from `app/api/deps.py`). Never `db: AsyncSession = Depends(...)`.
- Every decorator declares its response shape (`response_model=` for JSON, `response_class=` otherwise) and write methods declare `status_code=` (201 create, 204 delete). Raise `HTTPException` for error cases; list endpoints order deterministically and paginate.
- Transactions belong to the route via `async with db.begin():`; never call `db.commit()`/`db.rollback()` in request code.

Enforced by `scripts/check_route_conventions.py` (R1–R4) and `scripts/check_request_transaction_policy.py`.
