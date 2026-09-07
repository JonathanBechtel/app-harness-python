# app/services — business logic

- Stateless functions/classes taking `AsyncSession` first. Files end in `_service.py` (`.module-conventions.yml`).
- Services own the transaction boundary and sequencing; repositories do row access; routes do wiring.
- Internal DTOs are dataclasses; Pydantic models are for the HTTP edge only.
- No network I/O inside an open transaction — `app/utils/network_guard.py` raises outside prod. Do the call first, then open the transaction.
- Any new query must be indexed for the way it is filtered; ship the index and its migration in the same change.
