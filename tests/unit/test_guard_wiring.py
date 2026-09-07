"""Every guard script is wired in all three places: tasks.py, pre-commit, CI.

A guard that runs in one place but not another is exactly how "passes locally,
fails in CI" (or the reverse) happens.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
# Scripts run indirectly (by CI's round-trip step or the Makefile's roundtrip target).
INDIRECT = {"check_migration_teardown_residue.py", "check_deploy_freshness.py"}


def _guard_scripts() -> set[str]:
    return {p.name for p in (REPO / "scripts").glob("check_*.py")} - INDIRECT


def test_every_guard_is_in_precommit_tasks_and_ci() -> None:
    """Each scripts/check_*.py appears in .pre-commit-config.yaml, tasks.py, and ci.yml (directly or via `make checks`)."""
    precommit = (REPO / ".pre-commit-config.yaml").read_text()
    tasks = (REPO / "tasks.py").read_text()
    ci = (REPO / ".github/workflows/ci.yml").read_text()
    missing = []
    for script in sorted(_guard_scripts()):
        if script not in precommit:
            missing.append(f"{script} not in .pre-commit-config.yaml")
        if script not in tasks:
            missing.append(f"{script} not in tasks.py")
        if script not in ci and "tasks.py checks" not in ci and "make checks" not in ci:
            missing.append(f"{script} not in ci.yml")
    assert not missing, missing


def test_precommit_hooks_have_documented_names() -> None:
    """Every local hook has a human-readable name explaining what it guards."""
    text = (REPO / ".pre-commit-config.yaml").read_text()
    local = text.split("repo: local", 1)[1]
    ids = re.findall(r"- id: ([\w-]+)", local)
    names = re.findall(r"name: (.+)", local)
    assert len(ids) == len(names) and len(ids) >= 10
