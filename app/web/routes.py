"""Page routes. Thin: build a context dict, hand it to a template."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.config import settings

router = APIRouter(tags=["web"])


@router.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    """Landing page. Replace or delete once the app has a real front door."""
    templates: Jinja2Templates = request.app.state.templates
    return templates.TemplateResponse(
        request,
        "index.html",
        {"request": request, "env": settings.env, "release_sha": settings.release_sha},
    )
