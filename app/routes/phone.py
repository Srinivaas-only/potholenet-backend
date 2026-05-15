import logging
import os

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["phone"])


@router.get("/app", response_class=HTMLResponse, summary="Phone detection UI")
async def phone_app():
    """Serve the PotholeNet phone detection interface."""
    html_path = os.path.join(os.path.dirname(__file__), "..", "templates", "phone.html")
    with open(html_path, "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())