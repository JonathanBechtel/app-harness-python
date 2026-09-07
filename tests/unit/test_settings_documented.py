"""Reflective guards over Settings: every field documented, every secret scrubbed."""

from __future__ import annotations

import re
from pathlib import Path

from app.config import Settings
from app.observability.scrubbing import SECRET_SETTING_FIELDS, collect_secret_values

REPO = Path(__file__).resolve().parents[2]
_CREDENTIAL_SHAPE = re.compile(r"(key|secret|token|password|url)$")


def test_every_setting_is_documented_in_env_example() -> None:
    """Each Settings field appears (upper-cased) in .env.example so operators can find it."""
    example = (REPO / ".env.example").read_text(encoding="utf-8")
    missing = [
        name
        for name in Settings.model_fields
        if name.upper() not in example and name not in {"env"}
    ]
    assert not missing, f"document these in .env.example: {missing}"


def test_every_credential_shaped_setting_is_scrubbed() -> None:
    """A field named like a credential must be in SECRET_SETTING_FIELDS or logs can leak it."""
    credential_like = {n for n in Settings.model_fields if _CREDENTIAL_SHAPE.search(n)}
    unscrubbed = credential_like - set(SECRET_SETTING_FIELDS)
    assert not unscrubbed, f"add to SECRET_SETTING_FIELDS: {sorted(unscrubbed)}"


def test_scrub_list_names_only_real_fields() -> None:
    """A stale entry in SECRET_SETTING_FIELDS is an error, not a shrug."""
    stale = set(SECRET_SETTING_FIELDS) - set(Settings.model_fields)
    assert not stale, f"SECRET_SETTING_FIELDS names fields that no longer exist: {sorted(stale)}"


def test_collect_secret_values_includes_dsn_password() -> None:
    """The database password is scrubbed on its own, since error strings carry it without the URL."""
    s = Settings(database_url="postgresql+asyncpg://u:hunter2@h/db", secret_key="s3cr3t")
    values = collect_secret_values(s)
    assert "hunter2" in values
    assert "s3cr3t" in values
