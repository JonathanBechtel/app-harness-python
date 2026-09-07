"""Diff-scoped file-size ratchet for ``app/`` modules.

Failure this descends from: service files past 5,000 lines, and a merge of
35,000 insertions -- complexity beyond a reviewable unit. An absolute limit
would be ignored or a permanent wall of noise, so the rule measures the CHANGE
against a base ref:

    Ends under THRESHOLD                     pass
    Already over and the change grows it     fail
    Already over and the change shrinks it   pass
    New file over THRESHOLD                  fail
    Grew by more than DELTA_CAP              fail

Do not block the decomposition this rule exists to encourage: a pure split
creates new files full of moved lines. Rename detection (``git diff -M -C``)
and net-change evaluation across the whole changeset make a redistribution
pass; deleted files offset creation (capped at lines added in new files) but
never the growth of a file that already existed.

Escape hatch: a ``# discipline: file-size <reason>`` comment in the file.
Pre-commit runs this in warn mode; CI passes ``--enforce`` against the PR base,
and enforce mode fails closed on git errors.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _check_runner import merge_base, report, untracked_files  # noqa: E402
from _discipline import text_has_reasoned_waiver  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
THRESHOLD = 500
DELTA_CAP = 300
RULE = "file-size"
SCOPE = "app/"


@dataclass(frozen=True)
class FileChange:
    path: str
    old_lines: int
    new_lines: int
    waived: bool = False

    @property
    def is_new(self) -> bool:
        return self.old_lines == 0

    @property
    def is_deleted(self) -> bool:
        return self.new_lines == 0 and self.old_lines > 0


def _line_count(ref: str | None, path: str) -> int:
    if ref is None:
        p = REPO / path
        return len(p.read_text(encoding="utf-8").splitlines()) if p.exists() else 0
    out = subprocess.run(
        ["git", "show", f"{ref}:{path}"], capture_output=True, text=True, cwd=REPO, check=False
    )
    return len(out.stdout.splitlines()) if out.returncode == 0 else 0


def collect_changes(against: str) -> list[FileChange]:
    """Changed ``app/**/*.py`` files between the merge base and the working tree."""
    base = merge_base(against)
    out = subprocess.run(
        ["git", "diff", "-M", "-C", "--name-status", base, "--", SCOPE],
        capture_output=True,
        text=True,
        cwd=REPO,
        check=True,
    )
    changes: list[FileChange] = []
    for line in out.stdout.splitlines():
        parts = line.split("\t")
        status, paths = parts[0], parts[1:]
        if not paths or not paths[-1].endswith(".py"):
            continue
        if status.startswith(("R", "C")):
            old_path, new_path = paths[0], paths[1]
        elif status == "D":
            old_path, new_path = paths[0], ""
        else:
            old_path, new_path = (paths[0] if status != "A" else ""), paths[0]
        old = _line_count(base, old_path) if old_path else 0
        new = _line_count(None, new_path) if new_path else 0
        text = (
            (REPO / new_path).read_text(encoding="utf-8")
            if new_path and (REPO / new_path).exists()
            else ""
        )
        changes.append(
            FileChange(new_path or old_path, old, new, waived=text_has_reasoned_waiver(text, RULE))
        )
    for path_str in untracked_files((SCOPE,)):
        if path_str.endswith(".py") and (REPO / path_str).is_file():
            text = (REPO / path_str).read_text(encoding="utf-8")
            changes.append(
                FileChange(
                    path_str, 0, len(text.splitlines()), waived=text_has_reasoned_waiver(text, RULE)
                )
            )
    return changes


def evaluate(changes: list[FileChange]) -> tuple[list[str], list[str]]:
    """Return (violations, notes) for a changeset."""
    violations: list[str] = []
    notes: list[str] = []
    created = sum(c.new_lines for c in changes if c.is_new)
    deleted = sum(c.old_lines for c in changes if c.is_deleted)
    net = sum(c.new_lines - c.old_lines for c in changes if not c.is_deleted) - min(
        deleted, created
    )
    if net <= 0 and any(c.new_lines > THRESHOLD for c in changes):
        notes.append(f"net change {net:+d} lines across the changeset: redistribution, not growth")
        return violations, notes
    for c in changes:
        if c.is_deleted or c.waived:
            continue
        if c.is_new and c.new_lines > THRESHOLD:
            violations.append(
                f"{c.path}: new file is {c.new_lines} lines (> {THRESHOLD}); start it decomposed"
            )
        elif c.new_lines > THRESHOLD and c.new_lines > c.old_lines:
            violations.append(
                f"{c.path}: over {THRESHOLD} lines and must not grow ({c.old_lines} -> {c.new_lines})"
            )
        elif not c.is_new and c.new_lines - c.old_lines > DELTA_CAP:
            violations.append(
                f"{c.path}: grew by {c.new_lines - c.old_lines} lines in one change (cap {DELTA_CAP}); split it"
            )
    return violations, notes


def waiver_report() -> dict[str, int]:
    """Every app/ file carrying a justified waiver and its size."""
    result: dict[str, int] = {}
    for p in sorted((REPO / SCOPE).rglob("*.py")):
        text = p.read_text(encoding="utf-8")
        if text_has_reasoned_waiver(text, RULE):
            result[p.relative_to(REPO).as_posix()] = len(text.splitlines())
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="file-size ratchet")
    parser.add_argument("--against", default="HEAD")
    parser.add_argument(
        "--enforce", action="store_true", help="fail on violations (CI); default warns"
    )
    parser.add_argument("--report", action="store_true", help="print the waiver census as JSON")
    args = parser.parse_args(argv)
    if args.report:
        import json

        print(json.dumps(waiver_report(), indent=2))
        return 0
    try:
        changes = collect_changes(args.against)
    except subprocess.CalledProcessError as exc:
        print(f"file-size ratchet: git failed: {exc}", file=sys.stderr)
        return 1 if args.enforce else 0
    violations, notes = evaluate(changes)
    for note in notes:
        print(f"file-size ratchet: {note}")
    if not args.enforce and violations:
        print(
            "file-size ratchet (warning; CI enforces):\n  " + "\n  ".join(violations),
            file=sys.stderr,
        )
        return 0
    return report(
        "File-size ratchet",
        violations,
        footer=f"Decompose the module, or waive with `# discipline: {RULE} <reason>`.",
    )


if __name__ == "__main__":
    raise SystemExit(main())
