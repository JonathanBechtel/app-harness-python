"""Versioned prompt discovery."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.ai import prompts as prompts_pkg
from app.ai.prompts import loader


@pytest.fixture
def family(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> str:
    pkg = tmp_path / "greeting"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    for n in (1, 2):
        (pkg / f"v{n}.py").write_text(
            f'VERSION = "v{n}"\nTEMPLATE = "Hello {{name}} (v{n})"\n\ndef render(**kw):\n    return TEMPLATE.format(**kw)\n'
        )
    monkeypatch.setattr(prompts_pkg, "__path__", [str(tmp_path)])
    loader.clear_cache()
    yield "greeting"
    loader.clear_cache()


def test_latest_version_is_default(family: str) -> None:
    """With no pin, the highest vN module is loaded."""
    module = loader.load(family)
    assert module.VERSION == "v2"
    assert module.render(name="x") == "Hello x (v2)"


def test_env_pins_a_version(family: str, monkeypatch: pytest.MonkeyPatch) -> None:
    """PROMPT_<FAMILY>_VERSION selects an older version explicitly."""
    monkeypatch.setenv("PROMPT_GREETING_VERSION", "v1")
    loader.clear_cache()
    assert loader.load(family).VERSION == "v1"


def test_unknown_version_is_loud(family: str) -> None:
    """A missing version raises rather than silently falling back."""
    with pytest.raises(loader.PromptNotFoundError):
        loader.load(family, "v9")
