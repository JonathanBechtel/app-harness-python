"""Root test configuration: force sandbox-safe settings before app modules import.

CI often provides secrets as empty strings, and a developer's .env may point at a
real database. Settings are read at import time, so defaults are pinned here,
before anything under ``app`` is imported.
"""

from __future__ import annotations

import os

os.environ.setdefault("APP_ENV", "dev")
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("LOG_JSON", "0")
os.environ.setdefault("RELEASE_SHA", "testsha0000")
