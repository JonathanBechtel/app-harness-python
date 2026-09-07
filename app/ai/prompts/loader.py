"""Discover and load versioned prompt modules.

Adding a version requires no registration: ``app/ai/prompts/<family>/v<N>.py``
is found by name. The active version defaults to the highest; set
``PROMPT_<FAMILY>_VERSION=vN`` to pin. Bump the version (rather than editing in
place) whenever a change alters the tools mentioned, the output format, or the
response contract; small wording fixes edit in place.
"""

from __future__ import annotations

import importlib
import os
import pkgutil
import re
from functools import cache
from types import ModuleType

from app.ai import prompts as prompts_pkg

_VERSION_RE = re.compile(r"^v(\d+)$")


class PromptNotFoundError(LookupError):
    """No prompt module matched the family/version requested."""


def available_versions(family: str) -> list[str]:
    """Return the ``vN`` module names under ``app/ai/prompts/<family>``, ascending."""
    try:
        package = importlib.import_module(f"{prompts_pkg.__name__}.{family}")
    except ModuleNotFoundError as exc:
        raise PromptNotFoundError(f"no prompt family '{family}'") from exc
    names = [name.rsplit(".", 1)[-1] for _, name, _ in pkgutil.iter_modules(package.__path__)]
    versions = [n for n in names if _VERSION_RE.match(n)]
    return sorted(versions, key=lambda v: int(v[1:]))


@cache
def load(family: str, version: str | None = None) -> ModuleType:
    """Import the prompt module for ``family`` at ``version`` (default: env or latest)."""
    versions = available_versions(family)
    if not versions:
        raise PromptNotFoundError(f"prompt family '{family}' has no v<N> modules")
    chosen = version or os.getenv(f"PROMPT_{family.upper()}_VERSION") or versions[-1]
    if chosen not in versions:
        raise PromptNotFoundError(f"prompt '{family}/{chosen}' not found; have {versions}")
    module = importlib.import_module(f"{prompts_pkg.__name__}.{family}.{chosen}")
    for attr in ("VERSION", "TEMPLATE", "render"):
        if not hasattr(module, attr):
            raise PromptNotFoundError(f"prompt '{family}/{chosen}' lacks required attribute {attr}")
    return module


def clear_cache() -> None:
    """Forget loaded prompts (test isolation)."""
    load.cache_clear()
