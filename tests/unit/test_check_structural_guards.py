"""Entrypoint boundary and module-convention guards."""

from __future__ import annotations

from pathlib import Path

from tests.unit._script_loader import load_script

entry = load_script("check_runtime_entrypoints")
modules = load_script("check_module_conventions")


def test_e2_e3_flag_operator_tooling_references(tmp_path: Path) -> None:
    """An app module importing scripts.* or reading a .dockerignore-excluded path is reported."""
    p = tmp_path / "svc.py"
    p.write_text(
        'import scripts.foo\nfrom pathlib import Path\nCFG = Path("scripts/data/x.json")\n"""docs/ mention in a docstring is fine"""\n'
    )
    out = entry.check_e2_e3([p])
    assert any("E2" in v for v in out) and any("E3" in v for v in out), out


def test_excluded_dirs_read_from_dockerignore() -> None:
    """The excluded set comes from .dockerignore, so the two cannot drift."""
    assert {"scripts", "tests", "docs", "deploy", "evals"} <= entry.excluded_dirs()


def test_module_conventions_suffix_rule(tmp_path: Path, monkeypatch) -> None:
    """A file under an enrolled services/ directory must end with _service.py."""
    root = tmp_path / "app" / "services"
    root.mkdir(parents=True)
    (root / "__init__.py").write_text("")
    bad = root / "widgets.py"
    bad.write_text("x = 1\n")
    good = root / "widget_service.py"
    good.write_text("x = 1\n")
    monkeypatch.setattr(modules, "REPO", tmp_path)
    entries = [modules.Enrolled(root.resolve(), frozenset({"services"}))]
    assert modules.check_file(bad, entries) and "MODC001" in modules.check_file(bad, entries)[0]
    assert modules.check_file(good, entries) == []


def test_repo_is_clean() -> None:
    """The template satisfies its own structural guards."""
    assert entry.check_e1() + entry.check_e2_e3(entry.git_tracked_files(r"^app/")) == []
    assert modules.check_all() == []
