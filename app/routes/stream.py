import asyncio
import logging

from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import HTMLResponse, StreamingResponse

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
  <div id="meta">connecting...</div>
  <img id="frame" src="/stream.mjpg" alt="live ESP32-CAM stream">
</div>
<script>
const img = document.getElementById('frame');
const meta = document.getElementById('meta');
img.onload = () => { meta.textContent = 'streaming live'; };
img.onerror = () => { meta.textContent = 'stream connection failed — retrying'; setTimeout(() => { img.src = '/stream.mjpg?t=' + Date.now(); }, 1000); };
</script>
</body>
</html>
"""


@router.get("/stream", response_class=HTMLResponse, summary="Live camera preview page")
async def stream_page():
    return _PAGE


@router.get("/stream.mjpg", summary="MJPEG push stream of the latest frame")
async def mjpeg_stream():
    """multipart/x-mixed-replace — browser renders frames as they arrive."""

    async def gen():
        last_id = None
        try:
            while True:
                jpeg = app_main.frame_state.get("jpeg")
                if jpeg is not None and id(jpeg) != last_id:
                    last_id = id(jpeg)
                    yield (
                        b"--frame\r\n"
                        b"Content-Type: image/jpeg\r\n"
                        b"Content-Length: " + str(len(jpeg)).encode() + b"\r\n\r\n"
                        + jpeg + b"\r\n"
                    )
                await asyncio.sleep(0.03)
        except asyncio.CancelledError:
            return

    return StreamingResponse(
        gen(),
        media_type="multipart/x-mixed-replace; boundary=frame",
        headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
    )


@router.get("/latest-frame.jpg", summary="Most recent JPEG received from the ESP32")
async def latest_frame():
    jpeg = app_main.frame_state.get("jpeg")
    if jpeg is None:
        raise HTTPException(status_code=404, detail="No frame received yet")
    return Response(content=jpeg, media_type="image/jpeg")
