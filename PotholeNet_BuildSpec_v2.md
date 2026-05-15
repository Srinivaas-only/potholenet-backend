# PotholeNet — Mobile App Build Spec (v2)

> **Source of truth for the Z.AI build.** If anything in this doc contradicts what Z.AI generates, this doc wins. Read this before writing any code.

---

## 1. What this app IS and IS NOT

**IS:**
- A mobile-first React web app
- Designed to run full-screen on a phone browser
- Connected to a real ESP32-CAM over Wi-Fi (AP mode)
- A judge-facing hackathon demo AND a working product prototype
- Capable of offline operation after first load (service worker)
- Capable of switching to a simulated demo mode when no hardware is present

**IS NOT:**
- A desktop web app
- Wrapped in a fake "iPhone frame"
- Connected to any cloud backend during operation (the ESP32 is the network, no internet)
- A native iOS or Android app (PWA-capable but not packaged as native)
- Autonomous — the driver is always in control

---

## 2. Mobile-first principles — non-negotiable

### Viewport
```html
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no, viewport-fit=cover">
```
No zoom. No pinch. Full viewport including notch and home indicator areas.

### Safe areas
Every fixed top/bottom element uses `env(safe-area-inset-*)`:
```css
.top-bar    { padding-top:    env(safe-area-inset-top); }
.bottom-nav { padding-bottom: env(safe-area-inset-bottom); }
```

### Orientation
Portrait only. Lock with CSS:
```css
@media (orientation: landscape) and (max-width: 900px) {
  body > #app { display: none; }
  body::before {
    content: "Rotate to portrait";
    position: fixed; inset: 0;
    display: flex; align-items: center; justify-content: center;
    background: #0a0a0a; color: #888; font-family: sans-serif;
    z-index: 9999;
  }
}
```

### Touch targets
Minimum 48x48 CSS pixels for all interactive elements. Bottom nav buttons should be larger (56-60px) for thumb reach.

### No hover states
Use `:active` for press feedback. `:hover` does nothing useful on touchscreens.

### Wake lock
While in any reverse mode, request screen wake lock so the phone doesn't sleep:
```ts
let wakeLock: WakeLockSentinel | null = null;
async function requestWake() {
  try { wakeLock = await navigator.wakeLock.request('screen'); }
  catch (e) { console.warn('Wake lock failed', e); }
}
```

### Full screen (optional)
Provide a button to enter full screen mode. Don't force it — users sometimes need to access browser controls.

---

## 3. The 7 alert states — complete reference

State machine: states are derived from `(detections, gpsSpeed, streamLost)`. See section 7 for derivation logic.

### REVERSE_CLEAR — Safe
| Property | Value |
|----------|-------|
| Border color | `#22c55e` (green) |
| Border pulse | None (solid) |
| Border glow | `inset 0 0 20px rgba(34,197,94,0.15)` |
| Alert pill | "CLEAR" on green background |
| Mode badge | "REVERSE" in green |
| Detection pills | All blue (inactive) |
| Audio | Single soft chime on entry |
| Haptic | None |
| When triggered | No detections, GPS speed ≤ 5 km/h |

### REVERSE_APPROACHING — Slow down
| Property | Value |
|----------|-------|
| Border color | `#f59e0b` (orange) |
| Border pulse | 1.2s ease-in-out infinite |
| Border glow | `inset 0 0 30px rgba(245,158,11,0.2)` |
| Alert pill | "SLOW DOWN" on orange |
| Mode badge | "REVERSE" in orange |
| Detection pills | VEH pill turns purple (active) |
| Audio | Beep 800Hz/100ms every 1000ms |
| Haptic | Single vibration on entry (100ms) |
| When triggered | Vehicle bbox area 10-30% of frame |

### REVERSE_DANGER — Stop
| Property | Value |
|----------|-------|
| Border color | `#ef4444` (red) |
| Border pulse | 0.5s ease-in-out infinite (fast) |
| Border glow | `inset 0 0 40px rgba(239,68,68,0.25)` |
| Alert pill | "STOP" on red, slightly larger (14px) |
| Mode badge | "REVERSE" in red |
| Detection pills | VEH pill purple |
| Audio | Beep 1200Hz/80ms every 250ms |
| Haptic | Continuous pattern: vibrate(200, 100, 200, 100, ...) |
| When triggered | Vehicle bbox area > 30% of frame |

### REVERSE_PERSON — Person detected
| Property | Value |
|----------|-------|
| Border color | `#ef4444` (red) |
| Border pulse | 0.5s ease-in-out infinite (fast) |
| Border glow | `inset 0 0 40px rgba(239,68,68,0.3)` |
| Alert pill | "⚠ PERSON — STOP" on red |
| Mode badge | "REVERSE" in red |
| Detection pills | HUM pill turns orange (active) |
| Audio | Beep 1500Hz/60ms every 200ms + speechSynth("Stop") |
| Haptic | Continuous strong pattern |
| When triggered | Person/dog/cat detected at ANY distance — bypasses bbox size check |

**Why this exists:** The IP we're implementing has an "ethical value module." This state IS that module. The cost of a false positive (annoying beep when someone walks past 5m away) is trivial. The cost of a false negative (silent green while backing into a child) is catastrophic. Person detection MUST bypass distance.

### REVERSE_POTHOLE — Pothole detected
| Property | Value |
|----------|-------|
| Border color | `#ef4444` (red) |
| Border pulse | None (solid — not a collision, just a hazard) |
| Border glow | `inset 0 0 15px rgba(239,68,68,0.15)` |
| Alert pill | "POTHOLE DETECTED" on red |
| Mode badge | "REVERSE" in green (the mode is fine, the road is bad) |
| Detection pills | POT pill turns red |
| Audio | Beep 600Hz/150ms once |
| Haptic | Single vibration (150ms) |
| When triggered | Pothole class detected (simulated in v1, custom model in v2) |

### DRIVING — Monitoring + predictive warning
| Property | Value |
|----------|-------|
| Border color | `#22d3ee` (cyan) |
| Border pulse | None |
| Border glow | `inset 0 0 15px rgba(34,211,238,0.1)` |
| Alert pill | "MONITORING" on cyan |
| Mode badge | "DRIVING" in cyan |
| Detection pills | Active based on real detections |
| Hazard card | VISIBLE — shows predictive warning from cloud map (mocked) |
| Audio | Distinct soft chime on predictive warning + optional TTS "Pothole ahead in 120 meters" |
| Haptic | Single vibration on new predictive warning |
| When triggered | GPS speed > 5 km/h |

### DISCONNECTED — Camera lost
| Property | Value |
|----------|-------|
| Border color | `#666` (gray) |
| Border pulse | None |
| Border glow | None |
| Alert pill | "NO SIGNAL" on gray |
| Mode badge | "REVERSE" in gray |
| Detection pills | All blue (inactive) |
| Overlay | Full camera area: crossed circle icon + "CAMERA DISCONNECTED" + "Check Wi-Fi connection to PotholeNet-AP" |
| Info strip | STREAM shows "LOST" in red |
| Audio | Distinct warning chime (400Hz/200ms) + voice "Camera disconnected" |
| Haptic | Long single vibration (500ms) |
| When triggered | 3 consecutive heartbeat failures (6 seconds total) |

**Why this state matters:** This is the "fail visibly, never silently" design principle. Green = safe. Disconnected ≠ safe. A green border with a frozen image is the worst failure mode for a safety product.

---

## 4. Layout — exact dimensions

For a 390x844 viewport (iPhone 14 / Pixel 7 baseline):

```
┌─────────────────────────────────────┐  0
│ Status bar (system, env-inset-top)  │  ~44px (notch area)
├─────────────────────────────────────┤
│                                     │
│         CAMERA FEED (4:3)           │  ~440px
│         (with overlays)             │
│                                     │
├─────────────────────────────────────┤  484px
│ Info strip (60px)                   │
├─────────────────────────────────────┤  544px
│ Hazard card (80px, conditional)     │
├─────────────────────────────────────┤  544 or 624px
│                                     │
│         (empty space)               │  flex-grow
│                                     │
├─────────────────────────────────────┤
│ Bottom nav (80px + env-inset)       │  ~80px + 34px (home indicator)
└─────────────────────────────────────┘  844
```

The camera feed dominates the viewport. Everything else is secondary.

---

## 5. Component breakdown

```
src/
├── App.tsx                          # Routes + mode switcher
├── main.tsx
├── components/
│   ├── CameraView.tsx               # Container for camera + overlays
│   ├── camera/
│   │   ├── LiveStream.tsx           # <img src="http://192.168.4.1:81/stream" />
│   │   ├── DemoStream.tsx           # Canvas-based fake stream
│   │   └── StreamRouter.tsx         # Picks live or demo based on mode + heartbeat
│   ├── overlays/
│   │   ├── AlertBorder.tsx          # 4px border with pulse animation
│   │   ├── AlertPill.tsx            # Top-center status pill
│   │   ├── ModeBadge.tsx            # Top-left mode indicator
│   │   ├── DetectionStack.tsx       # Top-right pill stack (POT/HUM/VEH)
│   │   ├── BBoxOverlay.tsx          # SVG bounding boxes
│   │   ├── SpeedBadge.tsx           # Bottom-left speed
│   │   ├── ConfidenceBadge.tsx      # Bottom-right confidence
│   │   └── DisconnectOverlay.tsx    # Full-area disconnect message
│   ├── InfoStrip.tsx                # 4-col telemetry bar
│   ├── HazardCard.tsx               # Driving mode predictive warning
│   ├── BottomNav.tsx                # 5-button bottom navigation
│   ├── SettingsPanel.tsx            # Slide-up settings drawer
│   └── DemoControls.tsx             # Scene switcher (hidden by default)
├── hooks/
│   ├── useESPHeartbeat.ts           # Pings ESP32 every 2s, returns connected/lost
│   ├── useDetection.ts              # Runs TF.js on stream, returns Detection[]
│   ├── useGPS.ts                    # Geolocation API wrapper
│   ├── useAlertState.ts             # Derives alert state from inputs
│   ├── useWakeLock.ts               # Screen wake lock
│   ├── useVibration.ts              # Haptic feedback
│   └── useAudioCues.ts              # Web Audio API beep generator
├── lib/
│   ├── esp32.ts                     # ESP32 API wrappers (control, heartbeat)
│   ├── detection.ts                 # COCO-SSD wrapper
│   ├── alertLogic.ts                # deriveAlertState() function
│   └── simulation.ts                # Demo mode scene generator
├── types/
│   └── index.ts
├── constants/
│   ├── scenes.ts                    # All 7 state configs
│   └── colors.ts                    # Color constants
└── styles/
    └── globals.css
```

---

## 6. ESP32-CAM integration

### Live stream
```tsx
// components/camera/LiveStream.tsx
import { useRef, useEffect } from 'react';

export function LiveStream({ url, onError, onLoad }: Props) {
  const imgRef = useRef<HTMLImageElement>(null);
  
  // MJPEG over HTTP is rendered as an <img> tag directly
  return (
    <img
      ref={imgRef}
      src={url}
      alt="Live camera feed"
      onError={onError}
      onLoad={onLoad}
      style={{
        width: '100%',
        height: '100%',
        objectFit: 'cover',
        display: 'block',
      }}
      crossOrigin="anonymous"  // allows TF.js to read pixels
    />
  );
}
```

### Heartbeat hook
```tsx
// hooks/useESPHeartbeat.ts
export function useESPHeartbeat(baseUrl: string, enabled: boolean) {
  const [connected, setConnected] = useState(false);
  
  useEffect(() => {
    if (!enabled) return;
    let fails = 0;
    
    const check = async () => {
      try {
        const controller = new AbortController();
        const timeout = setTimeout(() => controller.abort(), 1500);
        const res = await fetch(`${baseUrl}/heartbeat`, { signal: controller.signal });
        clearTimeout(timeout);
        if (res.ok) {
          fails = 0;
          setConnected(true);
        } else {
          fails++;
        }
      } catch {
        fails++;
      }
      if (fails >= 3) setConnected(false);
    };
    
    check();
    const iv = setInterval(check, 2000);
    return () => clearInterval(iv);
  }, [baseUrl, enabled]);
  
  return connected;
}
```

### Control endpoint
```tsx
// lib/esp32.ts
export async function sendControl(baseUrl: string, params: Record<string, string>) {
  const qs = new URLSearchParams(params).toString();
  return fetch(`${baseUrl}/control?${qs}`, { method: 'GET' }).catch(() => null);
}

// Usage:
sendControl('http://192.168.4.1', { led: 'on' });
```

---

## 7. Alert state derivation

```ts
// lib/alertLogic.ts
export function deriveAlertState(
  detections: Detection[],
  gpsSpeedKmh: number,
  streamLost: boolean,
  manualMode?: AppScene  // optional override
): AppScene {
  if (manualMode) return manualMode;
  if (streamLost) return 'DISCONNECTED';
  if (gpsSpeedKmh > 5) return 'DRIVING';
  
  // Person/animal — instant red, no distance check
  if (detections.some(d => d.isHuman)) return 'REVERSE_PERSON';
  
  // Pothole
  if (detections.some(d => d.label === 'pothole')) return 'REVERSE_POTHOLE';
  
  // Vehicle — distance estimated by bbox area
  const FRAME_AREA = 320 * 240;
  const vehicles = detections.filter(d => d.isVehicle);
  if (vehicles.length > 0) {
    const largestArea = Math.max(...vehicles.map(d => d.bbox[2] * d.bbox[3]));
    if (largestArea > 0.3 * FRAME_AREA) return 'REVERSE_DANGER';
    if (largestArea > 0.1 * FRAME_AREA) return 'REVERSE_APPROACHING';
  }
  
  return 'REVERSE_CLEAR';
}
```

---

## 8. ML detection with TensorFlow.js

### Initial load
```tsx
import * as tf from '@tensorflow/tfjs';
import * as cocoSsd from '@tensorflow-models/coco-ssd';

// Use WebGL backend on mobile for GPU acceleration
await tf.setBackend('webgl');
await tf.ready();

const model = await cocoSsd.load({ base: 'lite_mobilenet_v2' });
// ~5-10MB download. Cache via service worker.
```

### Detection loop
```tsx
function useDetection(imgRef: RefObject<HTMLImageElement>, enabled: boolean) {
  const [detections, setDetections] = useState<Detection[]>([]);
  const [inferenceMs, setInferenceMs] = useState(0);
  const modelRef = useRef<cocoSsd.ObjectDetection | null>(null);
  
  useEffect(() => {
    cocoSsd.load({ base: 'lite_mobilenet_v2' }).then(m => modelRef.current = m);
  }, []);
  
  useEffect(() => {
    if (!enabled) return;
    let stopped = false;
    
    const loop = async () => {
      if (stopped) return;
      const img = imgRef.current;
      const model = modelRef.current;
      
      if (img && model && img.complete && img.naturalWidth > 0) {
        const start = performance.now();
        const preds = await model.detect(img);
        setInferenceMs(Math.round(performance.now() - start));
        
        const VALID = ['person', 'car', 'truck', 'motorcycle', 'bicycle', 'dog', 'cat', 'bus'];
        const filtered: Detection[] = preds
          .filter(p => p.score > 0.5 && VALID.includes(p.class))
          .map(p => ({
            label: p.class,
            confidence: Math.round(p.score * 100),
            bbox: p.bbox as [number, number, number, number],
            isHuman: ['person', 'dog', 'cat'].includes(p.class),
            isVehicle: ['car', 'truck', 'motorcycle', 'bicycle', 'bus'].includes(p.class),
          }));
        
        setDetections(filtered);
      }
      
      // Throttle: aim for ~5 FPS to keep phone cool
      setTimeout(loop, 200);
    };
    
    loop();
    return () => { stopped = true; };
  }, [imgRef, enabled]);
  
  return { detections, inferenceMs };
}
```

### Pothole detection
COCO-SSD does NOT detect potholes. For v1:
- Use simulation in DRIVING mode (random predictive warnings from "cloud")
- Show "POT" pill as a future detector slot, only activates in DEMO mode

For v2 (post-hackathon):
- Train YOLOv8n on Roboflow's pothole dataset
- Convert to TFJS format
- Load alongside COCO-SSD
- Run both models on each frame

---

## 9. PWA + service worker

```ts
// vite.config.ts
import { VitePWA } from 'vite-plugin-pwa';

export default {
  plugins: [
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['favicon.ico', 'robots.txt'],
      workbox: {
        globPatterns: ['**/*.{js,css,html,ico,png,svg,wasm,bin}'],
        runtimeCaching: [
          {
            urlPattern: /^https:\/\/tfhub\.dev/,
            handler: 'CacheFirst',
            options: {
              cacheName: 'tf-models',
              expiration: { maxEntries: 10, maxAgeSeconds: 60 * 60 * 24 * 30 }
            }
          },
          {
            // DO NOT cache the ESP32 stream — it's live
            urlPattern: /192\.168\.4\.1/,
            handler: 'NetworkOnly'
          }
        ]
      },
      manifest: {
        name: 'PotholeNet',
        short_name: 'PotholeNet',
        theme_color: '#0a0a0a',
        background_color: '#0a0a0a',
        display: 'standalone',
        orientation: 'portrait',
        icons: [
          { src: '/icon-192.png', sizes: '192x192', type: 'image/png' },
          { src: '/icon-512.png', sizes: '512x512', type: 'image/png' }
        ]
      }
    })
  ]
};
```

This means:
- First visit downloads everything
- After that, app works offline
- TF.js models cached for 30 days
- ESP32 stream is never cached (always live)

---

## 10. Settings panel

Slide-up drawer from bottom (Framer Motion). Triggered by gear icon top-right.

Fields:
- **Mode:** Live / Demo / Auto (try live, fall back to demo)
- **ESP32-CAM URL:** Default `http://192.168.4.1`. Editable for custom setups.
- **Sounds:** On / Off
- **Voice cues:** On / Off
- **Haptics:** On / Off
- **Wake lock:** On / Off
- **Detection threshold:** Slider 0.3 - 0.9, default 0.5
- **Auto demo on disconnect:** Checkbox

Persist in localStorage:
```ts
const settings = JSON.parse(localStorage.getItem('potholenet:settings') || '{}');
// merge with defaults...
```

Footer of settings:
- Version: "PotholeNet v0.1.0"
- IP attribution: "Implements UM IP PI 2017704203 — Value-Driven ML for CPHS"
- Disclaimer: "Assistive system. Driver retains full control at all times."

---

## 11. Demo mode

Triggered when:
- Setting is "Demo" explicitly, OR
- Setting is "Auto" and ESP32 unreachable after 3s, OR
- URL has `?demo=1`

In demo mode:
- Camera shown is the procedurally-drawn canvas from v1
- Detections are scripted per scene
- All 7 state-switcher buttons appear below the camera (hidden in live mode)
- "Play Auto Demo" button cycles through states automatically
- An indicator pill in the corner says "DEMO" to make it clear

---

## 12. Acceptance test

Build is done when, on my phone, I can:

- [ ] Open the app URL and see a full-screen mobile interface, no scrolling, no white space
- [ ] Connect phone to PotholeNet-AP and have the app detect it within 3 seconds
- [ ] See the real ESP32-CAM video stream rendered in the camera area
- [ ] Walk in front of the camera and have a red border + "PERSON — STOP" appear with bounding box
- [ ] Walk away and have the border return to green within 2 seconds
- [ ] Power off the ESP32-CAM and have the app switch to gray DISCONNECTED state within 7 seconds (NEVER green)
- [ ] Open settings, toggle to Demo mode, and see the simulated camera + scene switcher
- [ ] Add `?demo=1` to URL and have demo controls appear
- [ ] Reload the page with airplane mode on and have everything still work (service worker)
- [ ] Rotate phone to landscape and see "Rotate to portrait" message
- [ ] Hear distinct audio for each alert state when sounds are enabled
- [ ] Feel haptic feedback for danger/person states when haptics are enabled
- [ ] Screen stays on while in reverse mode (wake lock)

---

## 13. What to delete from the current build

- The phone frame mockup (`<div style="border: 2px solid #222; border-radius: 40px; ...">`)
- The desktop-centered `<div style="display: flex; justify-content: center; ...">` wrapper
- The fake status bar (9:41 / LTE / battery) — the real phone status bar is above
- The visible demo control buttons (move them behind `?demo=1`)

## 14. What to keep

- The 7-state state machine and config objects
- The color palette
- The component breakdown (refactored to the new structure above)
- The procedural canvas drawing — moved to DemoStream.tsx for demo mode
- The IP callouts for Person / Driving / Disconnected states
