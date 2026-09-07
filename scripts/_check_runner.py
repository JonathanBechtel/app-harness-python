"""Shared CLI scaffolding for the repo's ``scripts/check_*.py`` guards.

Three families of checker share this module:

* **Path-taking** (``check_route_conventions.py`` ...): receive changed files from
  pre-commit, or ``--all`` for a full git-tracked scan. ``run_cli`` provides the
  argv parsing, the vacuity defense (a changeset touching the checker itself
  forces a full scan), and uniform reporting.
* **Whole-tree** (``check_complexity_ratchet.py`` ...): own their argv, use only
  :func:`report`.
* **Diff-scoped at line granularity** (``check_test_docstrings.py`` ...): use
  :func:`changed_line_numbers` / :func:`diff_scoped_cli` so existing violations
  in untouched lines never fail the build.

Every family refuses to pass on an empty scan: "checked nothing" must never
print OK.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

RUNNER_FILENAME = "_check_runner.py"


def parse_args(argv: Sequence[str]) -> tuple[bool, list[Path]]:
    """Parse ``--all`` and positional paths; refuse both "nothing" spellings."""
    scan_all = False
    paths: list[Path] = []
    unknown: list[str] = []
    for arg in argv[1:]:
        if arg == "--all":
            scan_all = True
        elif arg.startswith("-"):
            unknown.append(arg)
        else:
            paths.append(Path(arg))
    script = Path(argv[0]).name if argv else "checker"
    if unknown:
        raise SystemExit(
            f"{script}: unknown option(s) {' '.join(unknown)}; takes file paths and --all only."
        )
    if not scan_all and not paths:
        raise SystemExit(
            f"{script}: no paths given and --all not passed; refusing to report OK after checking nothing."
        )
    return scan_all, paths


def is_full_scan_trigger(
    changed: Sequence[Path], script_path: Path, config_paths: Sequence[Path] = ()
) -> bool:
    """True when the checker, this runner, or a declared config file is in the changeset."""
    script_name = Path(script_path).name
    configs = {Path(c).resolve() for c in config_paths}
    for path in changed:
        resolved = path.resolve()
        if resolved.name in (script_name, RUNNER_FILENAME) or resolved in configs:
            return True
    return False


def git_tracked_files(pattern: str, suffix: str = ".py") -> list[Path]:
    """Git-tracked files matching ``pattern`` (regex on the repo-relative path)."""
    result = subprocess.run(["git", "ls-files"], capture_output=True, text=True, check=True)
    regex = re.compile(pattern)
    return [
        Path(line)
        for line in result.stdout.splitlines()
        if line.endswith(suffix) and regex.search(line)
    ]


_DIFF_FILE = re.compile(r"^\+\+\+ b/(.+)$")
_DIFF_HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")


EMPTY_TREE = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"  # git's well-known empty tree object


def merge_base(ref: str) -> str:
    """Merge base of ``ref`` and HEAD; ``ref`` itself on a shallow clone; the empty tree before the first commit.

    A repository with no commits yet (a fresh template checkout) has no HEAD, so every
    diff-scoped guard would crash. Diffing against the empty tree instead judges the
    whole tree as newly added, which is exactly what a first commit is.
    """
    # cat-file -e, not rev-parse --verify: the latter accepts any well-formed 40-hex
    # string (e.g. GitHub's all-zero `before` sha on a first push) without checking
    # that the object exists.
    probe = subprocess.run(
        ["git", "cat-file", "-e", f"{ref}^{{commit}}"],
        capture_output=True,
        text=True,
        check=False,
    )
    if probe.returncode != 0:
        return EMPTY_TREE
    try:
        out = subprocess.run(
            ["git", "merge-base", ref, "HEAD"], capture_output=True, text=True, check=True
        )
        return out.stdout.strip() or ref
    except subprocess.CalledProcessError:
        return ref


def untracked_files(pathspec: Sequence[str] = ()) -> list[str]:
    """Untracked, non-ignored files under ``pathspec`` (``git diff`` never shows these)."""
    result = subprocess.run(
        ["git", "ls-files", "--others", "--exclude-standard", "--", *pathspec],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.splitlines()


def changed_line_numbers(against: str, pathspec: Sequence[str] = ()) -> dict[str, set[int]]:
    """Added/modified line numbers per file: merge base vs working tree, plus every line of untracked files.

    Untracked files are included so a checker run from a checkout before ``git add``
    judges new files the same way pre-commit (staged) and CI (committed) will.
    """
    base = merge_base(against)
    result = subprocess.run(
        ["git", "diff", "--no-color", "--unified=0", base, "--", *pathspec],
        capture_output=True,
        text=True,
        check=True,
    )
    changed: dict[str, set[int]] = {}
    current: str | None = None
    for line in result.stdout.splitlines():
        file_match = _DIFF_FILE.match(line)
        if file_match:
            current = file_match.group(1)
            changed.setdefault(current, set())
            continue
        hunk = _DIFF_HUNK.match(line)
        if not hunk or current is None:
            continue
        start, count = int(hunk.group(1)), int(hunk.group(2) or "1")
        if count > 0:
            changed[current].update(range(start, start + count))
    for path_str in untracked_files(pathspec):
        path = Path(path_str)
        if path.is_file():
            changed[path_str] = set(
                range(1, len(path.read_text(encoding="utf-8", errors="ignore").splitlines()) + 1)
            )
    return changed


Finder = Callable[[Path, str, set[int]], list[str]]


@dataclass(frozen=True)
class DiffScope:
    """Which changed files a line-scoped checker looks at."""

    pathspec: tuple[str, ...]
    only_tests: bool = False


def diff_scoped_violations(against: str, scope: DiffScope, find: Finder) -> list[str]:
    """Run ``find`` over every changed file's changed lines."""
    violations: list[str] = []
    for path_str, lines in sorted(changed_line_numbers(against, scope.pathspec).items()):
        if not lines or not path_str.endswith(".py"):
            continue
        name = Path(path_str).name
        if scope.only_tests and not (name.startswith("test_") or name.endswith("_test.py")):
            continue
        path = Path(path_str)
        if path.is_file():
            violations.extend(find(path, path.read_text(encoding="utf-8"), lines))
    return violations


def diff_scoped_cli(
    argv: Sequence[str] | None, label: str, find: Finder, *, scope: DiffScope, footer: str = ""
) -> int:
    """Standard ``--against`` CLI for line-scoped checkers."""
    parser = argparse.ArgumentParser(description=label)
    parser.add_argument(
        "--against", default="HEAD", help="Git ref to compare against (CI passes the PR base)."
    )
    args = parser.parse_args(argv)
    try:
        violations = diff_scoped_violations(args.against, scope, find)
    except subprocess.CalledProcessError as exc:
        print(f"{label} failed to start: {exc}", file=sys.stderr)
        return 1
    return report(label, violations, footer=footer)


def report(
    label: str,
    violations: Sequence[str],
    *,
    ok_message: str | None = None,
    preamble: str = "",
    footer: str = "",
) -> int:
    """Print the uniform report and return the exit code (0 clean, 1 violations)."""
    if not violations:
        if ok_message:
            print(ok_message)
        return 0
    lines: list[str] = []
    if preamble:
        lines += [preamble, ""]
    lines.append(f"{label} failed:")
    lines += [f"  {v}" for v in violations]
    if footer:
        lines += ["", footer]
    print("\n".join(lines) + "\n", file=sys.stderr)
    return 1


@dataclass(frozen=True)
class CheckSpec:
    """A path-taking checker's callables and report text."""

    check_all: Callable[[], list[str]]
    check_paths: Callable[[Sequence[Path]], list[str]]
    label: str
    script_path: Path
    config_paths: Sequence[Path] = ()
    ok_message: str | None = None
    preamble: str = ""
    footer: str = ""


def run_cli(argv: Sequence[str], spec: CheckSpec) -> int:
    """Standard path-taking checker loop with the vacuity defense."""
    scan_all, paths = parse_args(argv)
    if not scan_all and paths and is_full_scan_trigger(paths, spec.script_path, spec.config_paths):
        scan_all = True
    try:
        violations = spec.check_all() if scan_all else spec.check_paths(paths)
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        print(f"{spec.label} failed to start: {exc}", file=sys.stderr)
        return 1
    return report(
        spec.label,
        violations,
        ok_message=spec.ok_message,
        preamble=spec.preamble,
        footer=spec.footer,
    )
