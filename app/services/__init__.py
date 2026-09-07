"""Business logic.

Services own sequencing, rules, and transaction boundaries; they take an
``AsyncSession`` first and never call commit()/rollback() in request paths (use
``async with db.begin():``). Files end in ``_service.py``.
"""
