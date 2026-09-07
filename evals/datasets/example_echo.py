"""Illustrative dataset: replace with real questions grounded in real data.

Kept minimal so the harness is exercisable without credentials.
"""

from __future__ import annotations

from evals.datasets import Question

QUESTIONS: list[Question] = [
    Question("echo-1", "ping", "echo: ping"),
    Question("echo-2", "2024-01-15 report", "echo: 2024-01-15 report"),
]


def score(answer: str, expected: str) -> float:
    """Exact-match scoring; real datasets usually normalise or extract first."""
    return 1.0 if answer.strip() == expected.strip() else 0.0
