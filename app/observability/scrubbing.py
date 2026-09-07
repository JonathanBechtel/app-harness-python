"""Redact configured secret values before a log record leaves the process.

No entropy heuristics, no "looks like a key" regexes: the scrubber takes the
values it *knows* are secret (from settings) and removes those exact strings.
That has no false positives and cannot be defeated by a credential format
nobody anticipated. The one shape-aware addition is the DSN password, which
appears in derived forms (an asyncpg error string) where the full URL does not.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from urllib.parse import urlsplit

if TYPE_CHECKING:  # pragma: no cover
    from app.config import Settings

REDACTED = "[REDACTED]"

# Settings fields whose value is a credential. Adding a secret to app/config.py
# means adding it here; tests/unit/test_settings_documented.py asserts this list
# covers every credential-shaped field.
SECRET_SETTING_FIELDS: tuple[str, ...] = (
    "secret_key",
    "database_url",
    "anthropic_api_key",
)

_PLACEHOLDERS = {"", "change-me"}


def collect_secret_values(settings: Settings) -> tuple[str, ...]:
    """Return every secret string the process holds, longest first."""
    values: set[str] = set()
    for field in SECRET_SETTING_FIELDS:
        value = getattr(settings, field, None)
        if not isinstance(value, str) or value in _PLACEHOLDERS:
            continue
        values.add(value)
        password = urlsplit(value).password if "://" in value else None
        if password:
            values.add(password)
    return tuple(sorted(values, key=len, reverse=True))


def scrub(text: str, secrets: tuple[str, ...]) -> str:
    """Replace every secret in ``text`` with a redaction marker."""
    for secret in secrets:
        if secret and secret in text:
            text = text.replace(secret, REDACTED)
    return text
