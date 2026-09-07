"""Suite definitions: which datasets, with what weights and gates."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Suite:
    name: str
    datasets: dict[str, float]  # module name -> weight
    repetitions: int = 3
    min_score: float = 0.8
    min_dataset_accuracy: float = 0.65
    notes: str = field(default="")
