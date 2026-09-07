"""Shared AST vocabulary: local-name resolution so an ``import ... as`` cannot switch a guard off.

Every AST checker decides whether a call matters by comparing its trailing name
against a set of interesting names. Python lets any of those be rebound
(``from sqlalchemy import delete as sa_delete``), and a guard that an alias can
disable is a guard whose coverage depends on import style. Resolve first.
"""

from __future__ import annotations

import ast
from collections.abc import Mapping


def trailing_name(node: ast.AST) -> str | None:
    """``os.path.join`` -> ``"join"``; ``Path`` -> ``"Path"``; else ``None``."""
    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, ast.Name):
        return node.id
    return None


def module_aliases(tree: ast.AST) -> dict[str, str]:
    """Map each renaming binding in a module to the trailing name it refers to."""
    aliases: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import | ast.ImportFrom):
            for spec in node.names:
                if spec.asname and spec.asname != spec.name:
                    aliases[spec.asname] = spec.name.rsplit(".", 1)[-1]
        elif isinstance(node, ast.Assign) and len(node.targets) == 1:
            _record(aliases, node.targets[0], node.value)
        elif isinstance(node, ast.AnnAssign):
            _record(aliases, node.target, node.value)
    return aliases


def _record(aliases: dict[str, str], target: ast.expr, value: ast.expr | None) -> None:
    if value is None or not isinstance(target, ast.Name):
        return
    bound = trailing_name(value)
    if bound is not None and bound != target.id:
        aliases[target.id] = bound


def resolve(name: str | None, aliases: Mapping[str, str]) -> str | None:
    """Follow ``name`` through ``aliases`` (cycle-safe)."""
    if name is None:
        return None
    seen: set[str] = set()
    while name in aliases and name not in seen:
        seen.add(name)
        name = aliases[name]
    return name


def resolved_call_name(call: ast.Call, aliases: Mapping[str, str]) -> str | None:
    """A call's trailing callee name, resolved."""
    return resolve(trailing_name(call.func), aliases)


def docstring_node_ids(tree: ast.AST) -> set[int]:
    """``id()`` of every docstring constant, so string-scanning checkers can skip prose."""
    ids: set[int] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        body = node.body
        if (
            body
            and isinstance(body[0], ast.Expr)
            and isinstance(body[0].value, ast.Constant)
            and isinstance(body[0].value.value, str)
        ):
            ids.add(id(body[0].value))
    return ids
