"""Line-scoped test-hygiene guards only judge changed lines."""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

from tests.unit._script_loader import load_script

docstrings = load_script("check_test_docstrings")
floats = load_script("check_test_float_comparisons")


def test_docstring_guard_only_sees_changed_functions(tmp_path: Path) -> None:
    """An undocumented test is flagged only when its span overlaps changed lines."""
    src = dedent("""
        def test_old():
            assert True

        def test_new():
            assert 1 == 1
    """).lstrip()
    p = tmp_path / "test_x.py"
    p.write_text(src)
    assert (
        docstrings.find_violations(p, src, {5})
        and "test_new" in docstrings.find_violations(p, src, {5})[0]
    )
    assert docstrings.find_violations(p, src, {99}) == []


def test_float_guard_requires_approx(tmp_path: Path) -> None:
    """A changed `assert x == 0.1` is flagged; `pytest.approx` and a reasoned waiver pass."""
    src = dedent("""
        import pytest
        def test_a(x):
            assert x == 0.1
            assert x == pytest.approx(0.1)
            assert x == 0.2  # discipline: float-compare exact sentinel value
    """).lstrip()
    p = tmp_path / "test_x.py"
    p.write_text(src)
    out = floats.find_violations(p, src, {3, 4, 5})
    assert len(out) == 1 and ":3:" in out[0], out
