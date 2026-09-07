# evals/ — LLM quality benchmarks

An eval is **not** a unit test. It measures answer quality against ground truth with repetition, so accuracy (how often right) and consistency (how stable) are both visible.

- `datasets/<name>.py` owns questions, expected answers, and dataset-specific scoring (`score(answer, expected) -> float in [0,1]`). Questions are **stationary**: absolute dates, no "yesterday".
- `analyzers/` are dataset-agnostic (accuracy, consistency). Keep them that way.
- `suites/<name>.py` weights datasets and declares pass/fail gates (`min_score`, `min_dataset_accuracy`).
- `runner.py` runs a suite: N repetitions per question through a `Responder` the app supplies (the same code path production uses — never HTTP), writes `evals/results/<suite>-<timestamp>.json`, and exits non-zero on a failed gate.
- Ground truth comes from data, not from the model's own narrative.
- Not in CI by default (cost, credentials). Run before shipping a prompt/model change and record the result in the PR.

Add a dataset with the `create-eval-dataset` workflow in `docs/guides/llm-features.md`.
