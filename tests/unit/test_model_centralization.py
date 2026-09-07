"""Model ids live in config and the role registry only."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from app.ai.registry import resolve
from app.config import Settings

REPO = Path(__file__).resolve().parents[2]
_MODEL_ID = re.compile(r"""["'](claude-[a-z0-9.-]+|gpt-[a-z0-9.-]+|gemini-[a-z0-9.-]+)["']""")
ALLOWED = {"app/config.py"}


def test_no_hardcoded_model_ids_outside_config() -> None:
    """Any literal model id under app/ outside app/config.py fails; use roles via app.ai.registry."""
    offenders = []
    for path in (REPO / "app").rglob("*.py"):
        rel = str(path.relative_to(REPO))
        if rel in ALLOWED:
            continue
        for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if _MODEL_ID.search(line):
                offenders.append(f"{rel}:{i}")
    assert not offenders, f"hard-coded model ids: {offenders}"


def test_role_resolves_to_defaults_then_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """A role without overrides uses the configured defaults; AI_<ROLE>_* env vars override it."""
    s = Settings(ai_default_provider="anthropic", ai_default_model="default-model")
    assert resolve("summarizer", s).model == "default-model"
    monkeypatch.setenv("AI_SUMMARIZER_MODEL", "other-model")
    monkeypatch.setenv("AI_SUMMARIZER_PROVIDER", "other")
    choice = resolve("summarizer", s)
    assert (choice.provider, choice.model) == ("other", "other-model")
