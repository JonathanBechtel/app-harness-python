"""Diff-scoped duplicate-code gate over ``app/`` and ``scripts/``.

AI-assisted codebases duplicate; ruff and mypy are structurally blind to
"this block already exists elsewhere". Runs pylint's similarity checker over
the whole tree (a duplicate is a property of a PAIR of files), then intersects
each R0801 finding's line range with the lines this changeset added or
modified. Fails when ``duplicated changed lines / changed lines`` exceeds
``DUPLICATE_CODE_MAX_PERCENT`` (default 3.0). A zero denominator passes; a tiny
diff needs at least ``MIN_CHANGED_LINES`` before the percentage counts.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _check_runner import (  # noqa: E402
    changed_line_numbers,
    git_tracked_files,
    report,
    untracked_files,
)

REPO = Path(__file__).resolve().parents[1]
SCOPES = ("app", "scripts")
MIN_SIMILARITY_LINES = 8
MIN_CHANGED_LINES = 20
_BLOCK = re.compile(r"^==(?P<file>[^:]+):\[(?P<start>\d+):(?P<end>\d+)\]$")


def run_pylint() -> str:
    """Pylint duplicate-code output over every tracked (and untracked) .py file in scope."""
    files = {str(p) for p in git_tracked_files(r"^(app|scripts)/")}
    files.update(f for f in untracked_files(SCOPES) if f.endswith(".py"))
    if not files:
        return ""
    cmd = [
        "pylint",
        "--disable=all",
        "--enable=duplicate-code",
        f"--min-similarity-lines={MIN_SIMILARITY_LINES}",
        "--ignore-imports=yes",
        "--ignore-docstrings=yes",
        "--ignore-signatures=yes",
        "--score=n",
        *sorted(files),
    ]
    out = subprocess.run(cmd, capture_output=True, text=True, cwd=REPO, check=False)
    if out.returncode not in (0, 4, 8, 12, 16, 20, 24, 28):  # pylint exit bits; 32 = usage error
        raise RuntimeError(f"pylint failed ({out.returncode}): {out.stderr.strip()[:500]}")
    return out.stdout


def duplicated_ranges(pylint_output: str) -> dict[str, set[int]]:
    """Line numbers pylint reports as duplicated, per file."""
    ranges: dict[str, set[int]] = {}
    for line in pylint_output.splitlines():
        m = _BLOCK.match(line.strip())
        if not m:
            continue
        file = m.group("file").replace(".", "/") + ".py"
        ranges.setdefault(file, set()).update(
            range(int(m.group("start")) + 1, int(m.group("end")) + 1)
        )
    return ranges


def evaluate(
    changed: dict[str, set[int]], duplicated: dict[str, set[int]], max_percent: float
) -> tuple[float, int, int, list[str]]:
    """Return (percent, dup_lines, changed_lines, offending files)."""
    total = sum(len(v) for v in changed.values())
    dup = 0
    offenders: list[str] = []
    for file, lines in changed.items():
        hit = lines & duplicated.get(file, set())
        if hit:
            dup += len(hit)
            offenders.append(
                f"{file}: {len(hit)} duplicated changed line(s) (lines {min(hit)}-{max(hit)})"
            )
    percent = (dup / total * 100.0) if total else 0.0
    return percent, dup, total, offenders


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--against", default="HEAD")
    args = parser.parse_args(argv)
    max_percent = float(os.environ.get("DUPLICATE_CODE_MAX_PERCENT", "3.0"))
    changed = {
        f: lines
        for f, lines in changed_line_numbers(args.against, SCOPES).items()
        if f.endswith(".py")
    }
    total = sum(len(v) for v in changed.values())
    if total < MIN_CHANGED_LINES:
        print(f"duplicate-code: {total} changed lines in scope (< {MIN_CHANGED_LINES}); skipping")
        return 0
    percent, dup, total, offenders = evaluate(changed, duplicated_ranges(run_pylint()), max_percent)
    summary = f"duplicate-code: {dup}/{total} changed lines duplicated ({percent:.1f}%, max {max_percent}%)"
    if percent <= max_percent:
        print(summary)
        return 0
    return report(
        "Duplicate-code gate",
        [summary, *offenders],
        footer="Extract the shared helper instead of copying it.",
    )


if __name__ == "__main__":
    raise SystemExit(main())
