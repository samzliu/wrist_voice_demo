"""Web server for API routes and static frontend. Run alongside the agent."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from livekit.api import AccessToken, VideoGrants
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, HTMLResponse, Response
from starlette.routing import Route, Mount
from starlette.staticfiles import StaticFiles

from .initial_deck import INTRO_DECK_HTML

load_dotenv(".env.local")

DECK_DIR = os.environ.get("WRIST_DECK_DIR", os.path.expanduser("~/slides"))
DECK_FILE = "onboarding.html"
STATIC_DIR = Path(__file__).parent.parent / "web" / "out"


def _deck_path() -> Path:
    return Path(DECK_DIR) / DECK_FILE


async def api_token(request: Request) -> JSONResponse:
    room = request.query_params.get("room", "onboarding-room")
    identity = request.query_params.get("identity", "human")

    token = (
        AccessToken(
            os.environ.get("LIVEKIT_API_KEY", ""),
            os.environ.get("LIVEKIT_API_SECRET", ""),
        )
        .with_identity(identity)
        .with_grants(VideoGrants(
            room=room,
            room_join=True,
            can_publish=True,
            can_subscribe=True,
            can_publish_data=True,
        ))
    )

    jwt = token.to_jwt()
    return JSONResponse({"token": jwt})


def _ensure_deck() -> None:
    """Create the intro deck if it doesn't exist."""
    path = _deck_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(INTRO_DECK_HTML, encoding="utf-8")


async def api_deck(request: Request) -> Response:
    path = _deck_path()
    _ensure_deck()
    html = path.read_text(encoding="utf-8")
    return HTMLResponse(html)


routes = [
    Route("/api/token", api_token),
    Route("/api/deck", api_deck),
]

if STATIC_DIR.exists():
    routes.append(Mount("/", app=StaticFiles(directory=str(STATIC_DIR), html=True)))

app = Starlette(routes=routes)
