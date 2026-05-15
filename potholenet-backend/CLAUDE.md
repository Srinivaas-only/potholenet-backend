# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

FastAPI backend for **PotholeNet** — crowdsourced road hazard detection. The server receives JPEG frames from an ESP32-CAM dashcam (or any client), runs two ML models, persists hazard reports in SQLite, and serves nearby-hazard queries to a Flutter phone app. Phone GPS state is pushed to the backend separately and used to auto-select detection mode.

## Commands

```bash
# Run locally (auto-reload enabled when DEBUG=true)
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

# Or via the module entrypoint (reads HOST/PORT/DEBUG from settings)
python -m app.main

# Build & run in Docker
docker build -t potholenet-backend .
docker run -p 8000:8000 --env-file .env potholenet-backend

# Install deps
pip install -r requirements.txt
```

Interactive API docs at `http://localhost:8000/docs`. There is no test suite, lint config, or formatter wired up.

Required configuration lives in `.env` (see `.env.example`); `ROBOFLOW_API_KEY` must be set or the pothole model will fail to load (the server still starts — see "Degradation behavior" below). All settings are loaded via `app/config.py::Settings` (pydantic-settings, cached with `lru_cache`).

## Architecture

### Request flow

1. **ESP32-CAM** captures frames and POSTs them to `/detect/dual-mode`. The phone app separately POSTs GPS state to `/location/update`. There is no per-request GPS — the backend reads the latest pushed value from a module-global dict.
2. **`app/routes/detect.py`** validates the upload, reads `gps_state` from `app.main`, picks a mode (`reverse` if `velocity_kmh < 0`, else `driving`), and calls the detector.
3. **`app/services/detector.py::Detector`** is a module-level singleton (`get_detector()`). It holds two models:
   - **Roboflow** custom pothole model (workspace/project/version in `Settings`) — heavy, ~300ms.
   - **YOLOv8n** (`ultralytics`) for humans/vehicles/animals — class IDs filtered via `TARGET_CLASSES` and the `HUMAN_CLASSES`/`VEHICLE_CLASSES`/`ANIMAL_CLASSES` sets.
   Both models infer on a tempfile written from the decoded image. In `reverse` mode pothole inference is skipped entirely (`pothole.detected` is forced false) to stay under ~100ms.
4. When a pothole is detected, the detect route calls `save_pothole_detection()` which inserts a `PotholeDetection` row using the cached phone GPS coords. This is **separate** from the user-submitted `HazardReport` flow below.

### Two distinct persistence paths — do not conflate them

- **`PotholeDetection`** (`app/models/db_models.py`) — automatic, written by `/detect/dual-mode` whenever the ML model fires. Raw telemetry.
- **`HazardReport`** — user-confirmed sightings submitted via `POST /reports`. `create_or_update_report()` in `app/services/hazard_store.py` runs **manual dedup**: scans every row in the table and, if any is within `DEDUP_RADIUS_M` (5m) and `DEDUP_WINDOW_DAYS` (30d), increments `severity_score` and updates `last_seen` instead of inserting. `GET /hazards` queries this table.
- **`RetrainingContribution`** — false-negative submissions from `POST /reports/false-negative`. Image files land in `retraining_queue/` (UUID-named); the DB row stores a JSON array of paths.

### Spatial queries are in-Python, not in SQL

`hazard_store.py` loads **all** rows and filters with `haversine()` from `app/services/geo_utils.py`. There is no spatial index — this is intentional for SQLite and will need to change if migrating to PostGIS. The 50-result cap in `query_hazards()` is applied after sorting by distance.

### Global mutable state

`app.main.gps_state` is a plain `dict` mutated by `/location/update` and read by `/detect/dual-mode`. The detect route imports it as `from app import main as app_main` to avoid a circular import at module load — keep that indirection if you touch the imports. This state is **not thread-safe and not multi-worker safe**; running uvicorn with `--workers > 1` will silently break mode auto-detection.

### Startup

`app/main.py`'s `startup_event` calls `create_tables()` (SQLAlchemy `Base.metadata.create_all`) and `detector.load_models()`. There are no migrations — schema changes require dropping `potholenet.db`. The `connect_args={"check_same_thread": False}` in `database.py` is SQLite-specific; remove it if switching engines.

### Degradation behavior

Model loads are wrapped in try/except and only set `models_loaded[...] = False` on failure — the server still starts. The detect routes check `models_loaded` and return empty results for the unavailable model rather than 5xx-ing. Keep this pattern when adding models.

### Time handling

All `datetime` values are timezone-aware UTC (`datetime.now(timezone.utc)`). Old SQLite rows can come back naive — `hazard_store.py` defensively re-attaches `tzinfo=timezone.utc` before comparisons. Preserve that when adding queries that compare timestamps.

## Out-of-scope files in this repo

`esp32_cam_firmware.py` and `esp32_setup_helper.py` are MicroPython device code and a host-side flashing helper — they run on the ESP32-CAM, not in the backend process. The `*_SETUP_GUIDE.md` / `*_QUICKSTART.md` / `IMPLEMENTATION_SUMMARY.md` files are user-facing docs and tend to drift from code; trust the code over the docs when they disagree.
