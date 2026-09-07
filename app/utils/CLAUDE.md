# app/utils — stateless helpers and infrastructure

`db.py` (engine, `get_session`, readiness probe) and `network_guard.py` (no network I/O in a transaction) are infrastructure. Everything else is a pure helper named `<domain>_utils.py`, placed near its consumers if it only has one.
