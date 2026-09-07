"""Enforce REST route conventions across ``app/api`` and ``app/web``.

Rules (each violation prints ``path:line: [CODE] message``):

  R1  Every ``@router.<method>(...)`` decorator declares a response shape:
      ``response_model=`` (JSON) or ``response_class=`` (HTML/streams/etc).
      Catches accidentally untyped APIs.
  R2  POST/PUT/PATCH/DELETE handlers returning JSON (no ``response_class=``)
      declare an explicit ``status_code=`` (201 create, 204 delete).
  R3  A handler parameter typed ``AsyncSession`` must be injected as
      ``DbSession`` (``app/api/deps.py``) or ``Annotated[AsyncSession, Depends(get_session)]``.
      No ``= Depends(...)`` defaults, no sessions built inline.
  R4  Every ``TemplateResponse(...)`` context dict contains a ``"request"`` key.

Names are resolved through the module's alias map, so ``import ... as`` cannot
turn a rule off. Escape hatch: ``# discipline: route-conventions <reason>`` on
the decorator or def line.
"""

from __future__ import annotations

import ast
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _astutil import module_aliases, resolve, trailing_name  # noqa: E402
from _check_runner import CheckSpec, git_tracked_files, run_cli  # noqa: E402
from _discipline import statement_has_reasoned_waiver  # noqa: E402

RULE = "route-conventions"
_HTTP_METHODS = {"get", "post", "put", "patch", "delete", "head", "options"}
_WRITE_METHODS = {"post", "put", "patch", "delete"}
_SESSION_ALIASES = {"DbSession"}


@dataclass(frozen=True)
class Violation:
    path: Path
    lineno: int
    code: str
    message: str

    def format(self) -> str:
        return f"{self.path}:{self.lineno}: [{self.code}] {self.message}"


def _router_method(decorator: ast.expr, aliases: Mapping[str, str]) -> str | None:
    if not isinstance(decorator, ast.Call) or not isinstance(decorator.func, ast.Attribute):
        return None
    if decorator.func.attr not in _HTTP_METHODS or not isinstance(decorator.func.value, ast.Name):
        return None
    if resolve(decorator.func.value.id, aliases) not in {"router", "app"}:
        return None
    return decorator.func.attr


def _kwarg(call: ast.Call, name: str) -> ast.keyword | None:
    return next((kw for kw in call.keywords if kw.arg == name), None)


def _annotation_is_session(
    annotation: ast.expr | None, aliases: Mapping[str, str]
) -> tuple[bool, bool]:
    """Return (is_session, is_properly_annotated)."""
    if annotation is None:
        return False, False
    name = resolve(trailing_name(annotation), aliases)
    if name in _SESSION_ALIASES:
        return True, True
    if name == "AsyncSession":
        return True, False
    if (
        isinstance(annotation, ast.Subscript)
        and resolve(trailing_name(annotation.value), aliases) == "Annotated"
    ):
        inner = (
            annotation.slice.elts if isinstance(annotation.slice, ast.Tuple) else [annotation.slice]
        )
        if inner and resolve(trailing_name(inner[0]), aliases) == "AsyncSession":
            has_depends = any(
                isinstance(e, ast.Call)
                and resolve(trailing_name(e.func), aliases) == "Depends"
                and e.args
                and resolve(trailing_name(e.args[0]), aliases) == "get_session"
                for e in inner[1:]
            )
            return True, has_depends
    return False, False


def _check_decorator(
    path: Path, func: ast.AST, decorator: ast.Call, method: str
) -> list[Violation]:
    out: list[Violation] = []
    name = getattr(func, "name", "?")
    if _kwarg(decorator, "response_model") is None and _kwarg(decorator, "response_class") is None:
        out.append(
            Violation(
                path,
                decorator.lineno,
                "R1",
                f"@router.{method} `{name}` needs response_model= or response_class=",
            )
        )
    if (
        method in _WRITE_METHODS
        and _kwarg(decorator, "response_class") is None
        and _kwarg(decorator, "status_code") is None
    ):
        out.append(
            Violation(
                path,
                decorator.lineno,
                "R2",
                f"@router.{method} `{name}` must declare an explicit status_code=",
            )
        )
    return out


def _check_signature(
    path: Path, func: ast.FunctionDef | ast.AsyncFunctionDef, aliases: Mapping[str, str]
) -> list[Violation]:
    out: list[Violation] = []
    for arg in [*func.args.posonlyargs, *func.args.args, *func.args.kwonlyargs]:
        is_session, ok = _annotation_is_session(arg.annotation, aliases)
        if is_session and not ok:
            out.append(
                Violation(
                    path,
                    arg.lineno,
                    "R3",
                    f"`{func.name}` param `{arg.arg}` must be `DbSession` (app/api/deps.py), not a bare AsyncSession",
                )
            )
    return out


def _check_template_calls(path: Path, tree: ast.AST, aliases: Mapping[str, str]) -> list[Violation]:
    out: list[Violation] = []
    for node in ast.walk(tree):
        if (
            not isinstance(node, ast.Call)
            or resolve(trailing_name(node.func), aliases) != "TemplateResponse"
        ):
            continue
        ctx = _kwarg(node, "context")
        context_node = (
            ctx.value if ctx else next((a for a in node.args if isinstance(a, ast.Dict)), None)
        )
        if context_node is None:
            if any(isinstance(a, ast.Name) for a in node.args):
                continue  # non-literal context: cannot verify statically
            out.append(
                Violation(
                    path,
                    node.lineno,
                    "R4",
                    "TemplateResponse(...) is missing a context dict containing `request`",
                )
            )
        elif isinstance(context_node, ast.Dict) and not any(
            isinstance(k, ast.Constant) and k.value == "request" for k in context_node.keys
        ):
            out.append(
                Violation(
                    path,
                    node.lineno,
                    "R4",
                    'TemplateResponse(...) context must include a "request" key',
                )
            )
    return out


def _check_file(path: Path) -> list[Violation]:
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    lines = source.splitlines()
    aliases = module_aliases(tree)
    violations: list[Violation] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        for decorator in node.decorator_list:
            method = _router_method(decorator, aliases)
            if method is None:
                continue
            assert isinstance(decorator, ast.Call)
            if statement_has_reasoned_waiver(lines, decorator.lineno, node.lineno, RULE):
                continue
            violations += _check_decorator(path, node, decorator, method)
            violations += _check_signature(path, node, aliases)
    violations += _check_template_calls(path, tree, aliases)
    return violations


def check_paths(paths: Sequence[Path]) -> list[str]:
    """Formatted violations for the given ``.py`` files."""
    found: list[Violation] = []
    for path in paths:
        if path.suffix == ".py" and path.is_file():
            found += _check_file(path)
    found.sort(key=lambda v: (str(v.path), v.lineno, v.code))
    return [v.format() for v in found]


def check_all() -> list[str]:
    """Every tracked route module; fails loudly rather than passing on an empty match."""
    files = git_tracked_files(r"^app/(api|web)/")
    if not files:
        raise ValueError("no files matched app/(api|web) -- guard would pass vacuously")
    return check_paths(files)


def main(argv: list[str]) -> int:
    return run_cli(
        argv,
        CheckSpec(
            check_all,
            check_paths,
            "Route conventions",
            Path(__file__),
            footer="See scripts/check_route_conventions.py for R1-R4.",
        ),
    )


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
