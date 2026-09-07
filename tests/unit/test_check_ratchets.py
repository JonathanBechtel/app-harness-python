"""Complexity and file-size ratchets: the decision tables, pinned."""

from __future__ import annotations

from tests.unit._script_loader import load_script

complexity = load_script("check_complexity_ratchet")
filesize = load_script("check_file_size_ratchet")
FileChange = filesize.FileChange
T = filesize.THRESHOLD


def test_complexity_compare_flags_rise_and_stale_entries() -> None:
    """A count above baseline fails; a count below baseline (stale headroom) also fails."""
    baseline = {"a.py": {"C901": 2}}
    assert complexity.compare({"a.py": {"C901": 3}}, baseline)
    assert complexity.compare({"a.py": {"C901": 1}}, baseline)
    assert complexity.compare({"a.py": {"C901": 2}}, baseline) == []
    assert complexity.compare({"b.py": {"C901": 1}}, baseline)


def test_complexity_baseline_matches_tree() -> None:
    """The committed baseline equals the measured tree exactly (no drift in either direction)."""
    assert complexity.compare(complexity.measure(), complexity.load_baseline()) == []


def test_filesize_verdicts() -> None:
    """Under threshold passes; oversized growth fails; shrink passes; new oversized fails; delta cap fails."""
    ok, _ = filesize.evaluate([FileChange("app/a.py", 100, 200)])
    assert ok == []
    grow, _ = filesize.evaluate([FileChange("app/big.py", T + 400, T + 450)])
    assert "must not grow" in grow[0]
    shrink, _ = filesize.evaluate([FileChange("app/big.py", T + 400, T + 350)])
    assert shrink == []
    new, _ = filesize.evaluate([FileChange("app/new.py", 0, T + 1)])
    assert "new file" in new[0]
    delta, _ = filesize.evaluate([FileChange("app/x.py", 10, 10 + filesize.DELTA_CAP + 1)])
    assert "grew by" in delta[0]


def test_filesize_pure_split_passes() -> None:
    """Deleting a 3000-line module and creating three 1000-line ones is a redistribution, not growth."""
    changes = [
        FileChange("app/god.py", 3000, 0),
        *(FileChange(f"app/part{i}.py", 0, 1000) for i in range(3)),
    ]
    violations, notes = filesize.evaluate(changes)
    assert violations == [] and notes


def test_filesize_waiver_exempts() -> None:
    """A justified file-size waiver exempts an oversized module."""
    violations, _ = filesize.evaluate([FileChange("app/big.py", T + 10, T + 20, waived=True)])
    assert violations == []
