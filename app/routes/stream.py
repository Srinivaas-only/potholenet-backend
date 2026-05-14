import logging

from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import HTMLResponse

from app import main as app_main

logger = logging.getLogger(__name__)

router = APIRouter(tags=["stream"])


_PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>PotholeNet camera</title>
<style>
  body { margin: 0; background: #111; color: #eee; font-family: -apple-system, system-ui, sans-serif; }
  #wrap { max-width: 800px; margin: 0 auto; padding: 12px; text-align: center; }
  #frame { max-width: 100%; height: auto; border-radius: 8px; background: #222; }
  #meta { font-size: 13px; opacity: 0.75; padding: 8px 0; }
</style>
</head>
<body>
<div id="wrap">
  <div id="meta">waiting for first frame...</div>
  <img id="frame" alt="latest frame from ESP32-CAM">
</div>
<script>
const img = document.getElementById('frame');
const meta = document.getElementById('meta');
function tick() {
  img.src = '/latest-frame.jpg?t=' + Date.now();
}
img.onload = () => {
  meta.textContent = 'frame received at ' + new Date().toLocaleTimeString();
};
img.onerror = () => {
  meta.textContent = 'no frame received yet';
};
tick();
setInterval(tick, 1000);
</script>
</body>
</html>
"""


@router.get("/stream", response_class=HTMLResponse, summary="Live camera preview page")
async def stream_page():
    return _PAGE


@router.get("/latest-frame.jpg", summary="Most recent JPEG received from the ESP32")
async def latest_frame():
    jpeg = app_main.frame_state.get("jpeg")
    if jpeg is None:
        raise HTTPException(status_code=404, detail="No frame received yet")
    return Response(content=jpeg, media_type="image/jpeg")
