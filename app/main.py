"""Composition root: wires settings, logging, middleware, routers, and lifespan.

Nothing here contains behaviour. Routers are registered by name so the route
table is readable in one place; ``tests/unit/test_route_table.py`` snapshots it.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from app.api.routes import health
from app.config import settings
from app.logging_config import setup_logging
from app.observability.middleware import RequestCorrelationMiddleware
from app.utils.db import dispose_engine
from app.web import routes as web_routes
from app.web.templating import register_template_filters

setup_logging()
logger = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).parent / "static"
TEMPLATES_DIR = Path(__file__).parent / "templates"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Startup/shutdown: nothing to warm today; dispose the engine on exit."""
    logger.info("startup env=%s release=%s", settings.env, settings.release_sha)
    yield
    await dispose_engine()
    logger.info("shutdown complete")


app = FastAPI(title="app-harness", lifespan=lifespan)
app.add_middleware(ProxyHeadersMiddleware, trusted_hosts=["*"])
app.add_middleware(RequestCorrelationMiddleware)

# Optional web layer. An API-only project can leave app/web untouched; it costs
# nothing until a template route is added (see app/web/CLAUDE.md).
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATES_DIR)
register_template_filters(templates.env)
app.state.templates = templates

app.include_router(health.router)
app.include_router(web_routes.router)
