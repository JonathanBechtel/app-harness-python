"""Run an eval suite and write a report.

python -m evals.runner --suite core [--repetitions N] [--responder module:attr]
"""

from __future__ import annotations

import argparse
import asyncio
import importlib
import json
import sys
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from pathlib import Path

from evals.analyzers import accuracy, consistency

Responder = Callable[[str], Awaitable[str]]
RESULTS = Path(__file__).parent / "results"


async def default_responder(question: str) -> str:
    """Credential-free responder using the app's FakeModelClient (echo)."""
    from app.ai.client import FakeModelClient

    result = await FakeModelClient().complete(role="eval", system="", prompt=question)
    return result.text


def load_responder(spec: str | None) -> Responder:
    if not spec:
        return default_responder
    module_name, attr = spec.split(":", 1)
    return getattr(importlib.import_module(module_name), attr)


async def run_dataset(name: str, responder: Responder, repetitions: int) -> dict:
    ds = importlib.import_module(f"evals.datasets.{name}")
    per_question = []
    for q in ds.QUESTIONS:
        scores = [ds.score(await responder(q.question), q.expected) for _ in range(repetitions)]
        per_question.append(
            {"id": q.id, "accuracy": accuracy(scores), "consistency": consistency(scores)}
        )
    return {
        "dataset": name,
        "accuracy": accuracy([p["accuracy"] for p in per_question]),
        "consistency": accuracy([p["consistency"] for p in per_question]),
        "questions": per_question,
    }


async def run_suite(suite_name: str, repetitions: int | None, responder: Responder) -> dict:
    suite = importlib.import_module(f"evals.suites.{suite_name}").SUITE
    reps = repetitions or suite.repetitions
    results = [await run_dataset(name, responder, reps) for name in suite.datasets]
    total_weight = sum(suite.datasets.values())
    score = sum(r["accuracy"] * suite.datasets[r["dataset"]] for r in results) / total_weight
    failed = [r["dataset"] for r in results if r["accuracy"] < suite.min_dataset_accuracy]
    return {
        "suite": suite.name,
        "ran_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "repetitions": reps,
        "score": round(score, 4),
        "passed": score >= suite.min_score and not failed,
        "failed_datasets": failed,
        "datasets": results,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--suite", default="core")
    parser.add_argument("--repetitions", type=int)
    parser.add_argument("--responder", help="module:attr of an async responder(question) -> str")
    args = parser.parse_args(argv)
    report = asyncio.run(run_suite(args.suite, args.repetitions, load_responder(args.responder)))
    RESULTS.mkdir(exist_ok=True)
    out = RESULTS / f"{report['suite']}-{report['ran_at'].replace(':', '')}.json"
    out.write_text(json.dumps(report, indent=2))
    print(f"suite={report['suite']} score={report['score']} passed={report['passed']} -> {out}")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
