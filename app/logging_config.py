"""Logging setup shared by the web app and every ``app/cli`` entrypoint.

One call configures both, on purpose: a scheduled job's output should be
queryable the same way a request's is.
"""

from __future__ import annotations

from logging.config import dictConfig
from typing import Any

from app.config import Settings, settings
from app.observability.scrubbing import collect_secret_values


def setup_logging(
    level: str | None = None,
    *,
    json_logs: bool | None = None,
    app_settings: Settings | None = None,
) -> None:
    """Configure root, uvicorn, and access loggers.

    Args:
        level: Root log level name; defaults to ``settings.log_level``.
        json_logs: Force JSON (True) or console (False). ``None`` defers to settings.
        app_settings: Settings to read defaults and the scrub list from.
    """
    resolved = app_settings if app_settings is not None else settings
    use_json = resolved.json_logs if json_logs is None else json_logs
    secrets = collect_secret_values(resolved)
    level = (level or resolved.log_level).upper()

    formatter: dict[str, Any] = (
        {"()": "app.observability.formatters.JsonFormatter", "secrets": secrets}
        if use_json
        else {
            "()": "app.observability.formatters.ConsoleFormatter",
            "secrets": secrets,
            "fmt": "%(asctime)s %(levelname)s [%(name)s] %(message)s",
            "datefmt": "%H:%M:%S",
        }
    )
    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {"default": formatter},
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "default",
                    "stream": "ext://sys.stdout",
                }
            },
            "root": {"level": level, "handlers": ["console"]},
            "loggers": {
                "uvicorn": {"level": level, "handlers": ["console"], "propagate": False},
                "uvicorn.error": {"level": level, "handlers": ["console"], "propagate": False},
                "uvicorn.access": {"level": "WARNING", "handlers": ["console"], "propagate": False},
                "sqlalchemy.engine": {"level": "WARNING"},
            },
        }
    )
