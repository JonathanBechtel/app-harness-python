"""Per-route query-count budgets.

THE BUMP-THE-NUMBER PROTOCOL: a failing budget means your change added
queries to that route. Accidental N+1 or serial waterfall -> fix it (batch the
load, selectinload, parallelise independent awaits); do not raise the budget.
A deliberate, necessary new query -> raise the budget here, in the same diff,
so the added per-request cost is visible in review. If a refactor LOWERS a
count, lower the budget too so the win is locked in.

Origin: a homepage that shipped a 25-query serial waterfall where every query
took <3ms. The cost was the count, not the SQL. Counting is what catches it.
"""

from __future__ import annotations

# route -> maximum SQL statements per request
BUDGETS: dict[str, int] = {
    "/health/db": 1,
}
