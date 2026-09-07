"""Docs-freshness guard: the template itself is clean, and placeholders trip once real code exists."""

from __future__ import annotations

from tests.unit._script_loader import load_script

guard = load_script("check_docs_freshness")


def test_template_tree_is_clean() -> None:
    """Every package is documented, placeholders are allowed (no real code yet), references resolve."""
    assert guard.check_package_docs() == []
    assert guard.check_references() == []
    assert guard.check_placeholders(guard._real_modules()) == []


def test_placeholders_fail_once_real_code_exists() -> None:
    """Given a real module, unresolved placeholder sections are reported."""
    out = guard.check_placeholders(["app/services/widget_service.py"])
    assert out and all("D2" in v for v in out)
