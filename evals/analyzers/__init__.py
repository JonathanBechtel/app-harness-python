"""Dataset-agnostic analyzers."""

from __future__ import annotations

from statistics import mean, pstdev


def accuracy(scores: list[float]) -> float:
    """Mean score across repetitions (1.0 = always right)."""
    return mean(scores) if scores else 0.0


def consistency(scores: list[float]) -> float:
    """1 - population stddev of scores (1.0 = identical every run)."""
    return 1.0 - pstdev(scores) if len(scores) > 1 else 1.0
