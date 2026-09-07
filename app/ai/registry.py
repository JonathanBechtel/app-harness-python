"""Role-based model routing.

Failure this descends from: model ids hard-coded in six modules that silently
diverged across three models, so nothing could state what the app was billed
for. Every call site names a *role* ("summarizer", "classifier"); the role
resolves here, from configuration, to a (provider, model) pair. Per-role
overrides come from ``AI_<ROLE>_PROVIDER`` / ``AI_<ROLE>_MODEL`` environment
variables; anything unset falls back to the defaults in ``app.config``.
``tests/unit/test_model_centralization.py`` fails the build if a model id
appears anywhere else under ``app/``.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from app.config import Settings, settings


@dataclass(frozen=True)
class ModelChoice:
    """Resolved (provider, model) for one role."""

    role: str
    provider: str
    model: str


def resolve(role: str, app_settings: Settings | None = None) -> ModelChoice:
    """Return the provider/model for ``role``.

    Args:
        role: A short lowercase role name, e.g. ``"summarizer"``.
        app_settings: Settings to read defaults from (defaults to process settings).
    """
    resolved = app_settings if app_settings is not None else settings
    key = role.upper().replace("-", "_")
    provider = (os.getenv(f"AI_{key}_PROVIDER") or "").strip() or resolved.ai_default_provider
    model = (os.getenv(f"AI_{key}_MODEL") or "").strip() or resolved.ai_default_model
    return ModelChoice(role=role, provider=provider, model=model)
