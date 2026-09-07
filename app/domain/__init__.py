"""Domain vocabulary: ORM-free value objects and pure rules.

Nothing here imports persistence, services, or the HTTP edge (import-linter
contract 2), so these types can be used at every layer without dragging
SQLAlchemy along.
"""
