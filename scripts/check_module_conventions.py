"""Enforce directory-scoped module placement and naming (``.module-conventions.yml``).

Enrollment is opt-in per directory. For each enrolled path and rule family
(helpers, models, services, transformers, repositories):

  MODC001  a file under ``<path>/<family>/`` must end with the family suffix;
  MODC002  a file at ``<path>/`` whose name carries a family suffix must live
           under that family's directory;
  MODC003  a file at ``<path>/`` whose shape looks like a family (a class
           deriving BaseModel/Enum -> models; service-layer imports -> services;
           only functions -> helpers) is flagged with a relocation hint;
  MODC004  an enrolled rule's directory must exist.

Flat layout is also accepted: ``<path>/foo_service.py`` directly under an
enrolled ``services`` path passes MODC002 when ``<path>`` itself IS the family
directory (e.g. ``app/services``).
"""

from __future__ import annotations

import ast
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _check_runner import CheckSpec, run_cli  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
CONFIG = REPO / ".module-conventions.yml"
SUFFIXES = {
    "helpers": "_helpers.py",
    "models": "_models.py",
    "services": "_service.py",
    "transformers": "_transformer.py",
    "repositories": "_repository.py",
}
MODEL_BASES = {"BaseModel", "Enum", "TypedDict", "SQLModel"}
SERVICE_MARKERS = ("app.repositories", "app.models", "AsyncSession")


@dataclass(frozen=True)
class Enrolled:
    path: Path
    rules: frozenset[str]


def load_config() -> list[Enrolled]:
    """Enrolled directories from the YAML config."""
    raw = yaml.safe_load(CONFIG.read_text(encoding="utf-8")) or {}
    entries: list[Enrolled] = []
    for i, item in enumerate(raw.get("enforced_directories", [])):
        rules = frozenset(item.get("rules", []))
        unknown = rules - SUFFIXES.keys()
        if unknown or not rules:
            raise ValueError(
                f"{CONFIG}: enforced_directories[{i}] rules must be a non-empty subset of {sorted(SUFFIXES)}"
            )
        entries.append(Enrolled((REPO / item["path"]).resolve(), rules))
    return entries


def _infer_family(tree: ast.Module) -> str | None:
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and any(
            getattr(b, "id", getattr(b, "attr", None)) in MODEL_BASES for b in node.bases
        ):
            return "models"
    imports = [n.module or "" for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)]
    names = {a.name for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) for a in n.names}
    if any(m.startswith(SERVICE_MARKERS[:2]) for m in imports) or "AsyncSession" in names:
        return "services"
    defs = [
        n for n in tree.body if isinstance(n, ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef)
    ]
    if defs and all(isinstance(n, ast.FunctionDef | ast.AsyncFunctionDef) for n in defs):
        return "helpers"
    return None


def check_file(path: Path, entries: Sequence[Enrolled]) -> list[str]:
    """Violations for one file."""
    resolved = path.resolve()
    if path.name == "__init__.py" or path.suffix != ".py":
        return []
    for entry in entries:
        try:
            rel = resolved.relative_to(entry.path)
        except ValueError:
            continue
        display = resolved.relative_to(REPO).as_posix()
        family_dir_is_root = entry.path.name in entry.rules
        if len(rel.parts) == 1:
            if family_dir_is_root:
                suffix = SUFFIXES[entry.path.name]
                return (
                    []
                    if path.name.endswith(suffix) or path.name.startswith("_")
                    else [f"{display}: MODC001 files in {entry.path.name}/ must end with {suffix}"]
                )
            for family in entry.rules:
                if path.name.endswith(SUFFIXES[family]):
                    return [
                        f"{display}: MODC002 belongs under {entry.path.relative_to(REPO).as_posix()}/{family}/"
                    ]
            tree = ast.parse(path.read_text(encoding="utf-8"))
            family = _infer_family(tree)
            if family in entry.rules:
                return [
                    f"{display}: MODC003 looks like {family} code; move it under {family}/ and name it *{SUFFIXES[family]}"
                ]
            return []
        family = rel.parts[0]
        if (
            family in entry.rules
            and not path.name.endswith(SUFFIXES[family])
            and not path.name.startswith("_")
        ):
            return [f"{display}: MODC001 files in {family}/ must end with {SUFFIXES[family]}"]
        return []
    return []


def check_paths(paths: Sequence[Path]) -> list[str]:
    """Violations for the given paths."""
    entries = load_config()
    out: list[str] = []
    for p in paths:
        if p.is_file():
            out += check_file(p, entries)
    return out


def check_all() -> list[str]:
    """Violations across every enrolled directory (+ MODC004 missing dirs)."""
    entries = load_config()
    out: list[str] = []
    for entry in entries:
        if not entry.path.exists():
            out.append(
                f"{entry.path.relative_to(REPO).as_posix()}: MODC004 enrolled directory does not exist"
            )
            continue
        for family in sorted(entry.rules):
            if entry.path.name != family and not (entry.path / family).is_dir():
                out.append(
                    f"{entry.path.relative_to(REPO).as_posix()}: MODC004 missing required {family}/ subdirectory"
                )
        for path in sorted(entry.path.rglob("*.py")):
            out += check_file(path, entries)
    return out


def main(argv: list[str]) -> int:
    return run_cli(
        argv,
        CheckSpec(
            check_all,
            check_paths,
            "Module conventions",
            Path(__file__),
            config_paths=(CONFIG,),
            footer="See docs/guides/module-conventions.md.",
        ),
    )


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
