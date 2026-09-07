"""Dataset modules. Each exposes QUESTIONS: list[Question] and score(answer, expected) -> float."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Question:
    id: str
    question: str
    expected: str
