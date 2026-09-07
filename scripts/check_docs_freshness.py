"""Agent documentation must describe the real application, not the template.

This repository starts as a template. The value of CLAUDE.md is that the next
agent reads an accurate description of THIS app; the failure mode is a project
six months in whose CLAUDE.md still says "describe your product here". Three
mechanical rules keep the docs honest:

  D1  Every top-level package under ``app/`` (a directory with ``__init__.py``)
      has its own ``CLAUDE.md`` and a row in ``app/CLAUDE.md``'s table.
  D2  Once the app has real code (any module under ``app/`` that is not part of
      the template's own skeleton), the ``<!-- template:placeholder -->``
      markers in CLAUDE.md and ``docs/architecture/overview.md`` must be gone.
      Replace each marked section with the truth about this app.
  D3  Every ``make``/``tasks.py`` target CLAUDE.md names must exist in
      ``tasks.py``'s registry, and every ``scripts/check_*.py`` must be
      mentioned in ``docs/guides/programmatic-code-discipline.md``'s catalog.

What counts as "real code" for D2: any ``app/**/*.py`` not listed in
``TEMPLATE_MODULES`` below. Keep that list current when you extend the template
itself; do not add product modules to it.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _check_runner import report  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
PLACEHOLDER = "<!-- template:placeholder -->"
PLACEHOLDER_DOCS = ("CLAUDE.md", "docs/architecture/overview.md")
GUARD_CATALOG = "docs/guides/programmatic-code-discipline.md"

TEMPLATE_MODULES: frozenset[str] = frozenset(
    {
        "app/__init__.py",
        "app/config.py",
        "app/logging_config.py",
        "app/main.py",
        "app/api/__init__.py",
        "app/api/deps.py",
        "app/api/routes/__init__.py",
        "app/api/routes/health.py",
        "app/web/__init__.py",
        "app/web/routes.py",
        "app/web/templating.py",
        "app/services/__init__.py",
        "app/repositories/__init__.py",
        "app/domain/__init__.py",
        "app/models/__init__.py",
        "app/models/base.py",
        "app/schemas/__init__.py",
        "app/schemas/health.py",
        "app/cli/__init__.py",
        "app/cli/_runner.py",
        "app/cli/healthcheck.py",
        "app/ai/__init__.py",
        "app/ai/registry.py",
        "app/ai/client.py",
        "app/ai/prompts/__init__.py",
        "app/ai/prompts/loader.py",
        "app/observability/__init__.py",
        "app/observability/context.py",
        "app/observability/middleware.py",
        "app/observability/scrubbing.py",
        "app/observability/formatters.py",
        "app/utils/__init__.py",
        "app/utils/db.py",
        "app/utils/network_guard.py",
    }
)


def _packages() -> list[Path]:
    return sorted(
        p.parent for p in (REPO / "app").rglob("__init__.py") if "__pycache__" not in p.parts
    )


def _real_modules() -> list[str]:
    modules = [
        p.relative_to(REPO).as_posix()
        for p in (REPO / "app").rglob("*.py")
        if "__pycache__" not in p.parts
    ]
    return sorted(m for m in modules if m not in TEMPLATE_MODULES)


def check_package_docs() -> list[str]:
    """D1: every app package has a CLAUDE.md and a row in app/CLAUDE.md."""
    out: list[str] = []
    table = (
        (REPO / "app/CLAUDE.md").read_text(encoding="utf-8")
        if (REPO / "app/CLAUDE.md").exists()
        else ""
    )
    for pkg in _packages():
        rel = pkg.relative_to(REPO / "app")
        if rel == Path(".") or len(rel.parts) != 1:
            continue  # subpackages are covered by their top-level package's CLAUDE.md
        if not (pkg / "CLAUDE.md").exists():
            out.append(f"D1 {pkg.relative_to(REPO).as_posix()}/ has no CLAUDE.md")
        top = rel.parts[0]
        if f"`{top}/`" not in table:
            out.append(f"D1 app/CLAUDE.md has no table row for `{top}/`")
    return sorted(set(out))


def check_placeholders(real_modules: list[str]) -> list[str]:
    """D2: once real code exists, placeholder markers must be resolved."""
    if not real_modules:
        return []
    out: list[str] = []
    for doc in PLACEHOLDER_DOCS:
        text = (REPO / doc).read_text(encoding="utf-8") if (REPO / doc).exists() else ""
        count = text.count(PLACEHOLDER)
        if count:
            out.append(
                f"D2 {doc} still has {count} template placeholder section(s); the app has real code ({real_modules[0]} ...). Describe the actual app."
            )
    return out


def _task_names() -> set[str]:
    """Task names registered in tasks.py (the single definition of every project task)."""
    import importlib.util

    spec = importlib.util.spec_from_file_location("tasks", REPO / "tasks.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules.setdefault("tasks", module)  # dataclasses resolve annotations via sys.modules
    spec.loader.exec_module(module)
    return set(module.TASKS)


def check_references() -> list[str]:
    """D3: make/tasks targets named in CLAUDE.md exist; every guard script is catalogued."""
    out: list[str] = []
    claude = (REPO / "CLAUDE.md").read_text(encoding="utf-8")
    targets = _task_names()
    named = set(re.findall(r"`make ([a-zA-Z0-9_.-]+)", claude)) | set(
        re.findall(r"`python tasks\.py ([a-zA-Z0-9_.-]+)", claude)
    )
    for target in sorted(named):
        if target not in targets:
            out.append(f"D3 CLAUDE.md names task `{target}` but tasks.py has no such task")
    catalog = (
        (REPO / GUARD_CATALOG).read_text(encoding="utf-8")
        if (REPO / GUARD_CATALOG).exists()
        else ""
    )
    for script in sorted((REPO / "scripts").glob("check_*.py")):
        if script.name not in catalog:
            out.append(f"D3 scripts/{script.name} is not in the guard catalog ({GUARD_CATALOG})")
    return out


def main() -> int:
    violations = check_package_docs() + check_placeholders(_real_modules()) + check_references()
    return report(
        "Docs freshness",
        violations,
        ok_message="docs freshness: OK",
        footer="Agent docs must describe this app. See docs/guides/self-documentation.md.",
    )


if __name__ == "__main__":
    raise SystemExit(main())
