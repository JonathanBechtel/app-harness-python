"""Row-level data access.

Repositories take a session, read/write ORM models, and never own
commit/rollback or workflow. Files end in ``_repository.py``.
"""
