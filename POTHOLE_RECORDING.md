# Pothole Detection Recording

## Automatic Recording

Every time a pothole is detected, the backend automatically saves it with location, time, and confidence to the database.

## What Gets Recorded

When a pothole is detected:
- **Location**: Latitude/Longitude (from phone GPS at detection time)
- **Time**: Exact timestamp of detection 
- **Date**: Included in ISO 8601 timestamp format
- **Confidence**: Detection confidence score (0-1)
- **Speed**: Vehicle velocity at detection
- **Mode**: REVERSE or DRIVING
- **Count**: Number of potholes detected in frame

## Database Storage

Potholes are automatically saved to SQLite database table `pothole_detections` with these fields:

| Field | Type | Description |
|-------|------|-------------|
| `id` | TEXT | Unique detection ID (UUID) |
| `latitude` | FLOAT | Phone GPS latitude at detection |
| `longitude` | FLOAT | Phone GPS longitude at detection |
| `confidence` | FLOAT | Detection confidence (0-1) |
| `velocity_kmh` | FLOAT | Vehicle speed at detection |
| `mode` | TEXT | "REVERSE" or "DRIVING" |
| `detected_at` | DATETIME | Timestamp of detection (ISO 8601) |
| `pothole_count` | INTEGER | Number of potholes in frame |

## Example Detection Record

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "latitude": 3.1234,
  "longitude": 101.5678,
  "confidence": 0.92,
  "velocity_kmh": 45.5,
  "mode": "DRIVING",
  "pothole_count": 1,
  "detected_at": "2026-05-13T15:30:45.123456"
}
```

## Accessing Recorded Potholes

Query the SQLite database directly:

```bash
# Query recent detections (last 10)
sqlite3 potholenet.db "SELECT latitude, longitude, confidence, detected_at FROM pothole_detections ORDER BY detected_at DESC LIMIT 10;"

# Find potholes in a geographic region
sqlite3 potholenet.db "SELECT id, latitude, longitude, confidence FROM pothole_detections WHERE latitude BETWEEN 3.1 AND 3.2 AND longitude BETWEEN 101.5 AND 101.6;"

# Count potholes by day
sqlite3 potholenet.db "SELECT DATE(detected_at) as date, COUNT(*) as count FROM pothole_detections GROUP BY DATE(detected_at) ORDER BY date DESC;"

# High-confidence detections (>0.8)
sqlite3 potholenet.db "SELECT latitude, longitude, confidence, velocity_kmh FROM pothole_detections WHERE confidence > 0.8 ORDER BY detected_at DESC;"
```

## Requirements for Recording

For full pothole recording with location:

1. **Phone sends GPS coordinates** via `POST /location/update`:
   ```bash
   curl -X POST http://192.168.4.1:8000/location/update \
     -F "velocity_kmh=45.5" \
     -F "latitude=3.1234" \
     -F "longitude=101.5678"
   ```

2. **Pothole detected in DRIVING mode** (Roboflow model must be active)

3. **Backend has SQLite database** (auto-created on startup at `potholenet.db`)

### What if phone doesn't send coordinates?

If the phone doesn't send latitude/longitude, the pothole detection is still recorded with:
- `latitude` = NULL
- `longitude` = NULL
- All other fields recorded normally

This allows you to still track confidence scores and velocity, but you won't know the location.

## Testing Recording

```bash
# 1. Start backend
python app/main.py

# 2. Send phone location update
curl -X POST http://192.168.4.1:8000/location/update \
  -F "velocity_kmh=50.0" \
  -F "latitude=3.1234" \
  -F "longitude=101.5678"

# 3. Send test image with pothole
curl -X POST http://192.168.4.1:8000/detect/dual-mode \
  -F "image=@test_pothole.jpg" \
  -F "mode=driving"

# 4. Query the database
sqlite3 potholenet.db "SELECT * FROM pothole_detections ORDER BY detected_at DESC LIMIT 1;"

# 5. Expected output:
# 550e8400-e29b-41d4-a716-446655440000|3.1234|101.5678|0.92|50.0|DRIVING|2026-05-13T15:30:45.123456|1
```

## Integration with Phone App

Your phone app needs to:

1. **Get GPS Location** (latitude, longitude)
2. **Calculate Velocity** from location deltas:
   ```python
   # Pseudocode
   distance = calculate_distance(prev_lat, prev_lon, curr_lat, curr_lon)  # meters
   time_delta = current_time - prev_time  # seconds
   velocity_kmh = (distance / time_delta) * 3.6
   ```
3. **Send every 1-2 seconds** via POST /location/update

When the ESP32 captures a frame:
- Backend detects if it's a pothole using Roboflow
- Uses the latest phone GPS data for location
- Records detection with full metadata to database

## Troubleshooting

**Q: Detections saved but latitude/longitude are NULL?**
- A: Phone app is not sending coordinates via `/location/update`. Check phone app sends latitude + longitude parameters.

**Q: Database file not created?**
- A: Backend hasn't started properly. Check `python app/main.py` runs without errors.

**Q: Can't connect to database?**
- A: Make sure you're in the backend directory and using correct path: `sqlite3 potholenet.db`

**Q: Confidence score seems low?**
- A: Roboflow model quality depends on training data. High confidence = high-quality detection (>0.8 recommended).
