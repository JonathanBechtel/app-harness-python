"""Core benchmark suite. Replace example_echo with the app's real datasets."""

from __future__ import annotations

from evals.suites import Suite

SUITE = Suite(
    name="core",
    datasets={"example_echo": 1.0},
    repetitions=3,
    min_score=0.8,
    min_dataset_accuracy=0.65,
    notes="Template placeholder suite; gates are meaningful only once real datasets exist.",
)
