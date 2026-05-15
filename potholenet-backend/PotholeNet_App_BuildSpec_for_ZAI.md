# PotholeNet — App Interface Build Spec for Z.AI

> **What this document is:** A complete, unambiguous instruction set for an AI coding agent (Claude Code, Cursor, or similar) to build the PotholeNet demo app as a React web application. Every design decision is made. The agent's job is to implement, not interpret.

> **What to build:** A mobile-first React web app that simulates the PotholeNet reverse camera experience. This is a **judge-facing demo**, not a production app. It must look and feel like a real product, but it uses simulated data — no real ESP32-CAM connection, no real ML inference, no real cloud backend.

> **Why React and not Flutter:** The hackathon demo runs on a laptop browser projected to judges. React + Vite is faster to build, easier to demo, and doesn't need a phone. The actual production app would be Flutter — this is the demo only.

---

## 1. PROJECT SETUP

```
Framework: React 18+ with Vite
Language: TypeScript
Styling: Tailwind CSS + custom CSS variables for the color system
State: React useState/useReducer (no Redux — overkill for a demo)
Animations: Framer Motion for transitions, CSS animations for pulses
Icons: Lucide React
Deployment: Static build, servable from any local HTTP server
```

### File structure
```
potholenet-demo/
├── index.html
├── package.json
├── tailwind.config.js
├── tsconfig.json
├── vite.config.ts
├── src/
│   ├── main.tsx
│   ├── App.tsx
│   ├── components/
│   │   ├── CameraFeed.tsx        # Canvas-based simulated camera view
│   │   ├── AlertBorder.tsx       # Traffic-light border overlay
│   │   ├── AlertLabel.tsx        # Top-center status pill (CLEAR/SLOW DOWN/STOP)
│   │   ├── ModeBadge.tsx         # Top-left mode indicator (REVERSE/DRIVING)
│   │   ├── DetectionStack.tsx    # Top-right detection pill indicators
│   │   ├── BoundingBoxOverlay.tsx # SVG bounding boxes over camera feed
│   │   ├── SpeedBadge.tsx        # Bottom-left speed display
│   │   ├── ConfidenceBadge.tsx   # Bottom-right confidence display
│   │   ├── InfoStrip.tsx         # Stream/GPS/Cloud/Inference status bar
│   │   ├── HazardCard.tsx        # Predictive warning card (driving mode)
│   │   ├── DisconnectOverlay.tsx # Camera disconnected state
│   │   ├── BottomNav.tsx         # Servo controls + report + map buttons
│   │   └── DemoControls.tsx      # Scene switcher buttons (for demo only)
│   ├── hooks/
│   │   ├── useAppState.ts        # Central state management
│   │   └── useSimulation.ts      # Auto-cycling demo sequences
│   ├── types/
│   │   └── index.ts              # All TypeScript interfaces
│   ├── constants/
│   │   └── scenes.ts             # Predefined scene configurations
│   └── styles/
│       └── globals.css           # CSS variables, animations, base styles
```

---

## 2. DESIGN SYSTEM — EXACT SPECIFICATIONS

### Color palette (CSS variables — define in globals.css)

```css
:root {
  /* App background */
  --pn-bg: #0a0a0a;
  --pn-surface: #111111;
  --pn-surface-raised: #1a1a1a;
  --pn-border: #2a2a2a;
  --pn-border-subtle: #1a1a1a;

  /* Traffic light system — THE core visual language */
  --pn-green: #22c55e;
  --pn-green-glow: rgba(34, 197, 94, 0.15);
  --pn-orange: #f59e0b;
  --pn-orange-glow: rgba(245, 158, 11, 0.2);
  --pn-red: #ef4444;
  --pn-red-glow: rgba(239, 68, 68, 0.25);

  /* Functional colors */
  --pn-cyan: #22d3ee;       /* Driving mode, inference, confidence */
  --pn-purple: #a855f7;     /* Vehicle detection */
  --pn-blue: #60a5fa;       /* Default/inactive detection pills */
  --pn-gray: #666666;       /* Disconnected state */

  /* Text */
  --pn-text-primary: #ffffff;
  --pn-text-secondary: #999999;
  --pn-text-muted: #555555;

  /* Typography */
  --pn-font-ui: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
  --pn-font-mono: 'JetBrains Mono', 'SF Mono', 'Fira Code', monospace;
}
```

### Typography rules
- Mode badge, detection pills, speed, confidence, info strip values: `--pn-font-mono`, all caps
- Alert labels, hazard card text, button labels: `--pn-font-ui`
- Font sizes: 10px (pills, micro labels), 11px (secondary info), 12px (info strip), 13px (alert label), 18px (speed number)
- Font weight: 400 for body, 500 for labels and values, never 600 or 700

### Layout
- Phone frame: max-width 390px, aspect-ratio 9/19.5, centered on screen
- Camera feed area: aspect-ratio 4/3, full width within frame
- All overlays on camera feed use absolute positioning with z-index layering
- Bottom nav is fixed to bottom of phone frame

### Border radius
- Phone frame: 40px (simulates iPhone)
- Alert label pill: 20px
- Mode badge, detection pills: 4px
- Buttons: 8px
- Hazard card: 10px
- Speed/confidence badges: 6px

---

## 3. APP STATES — COMPLETE STATE MACHINE

The app has exactly **7 states**. Each state defines EVERY visual element. The agent must implement ALL of them with zero ambiguity.

### State: `REVERSE_CLEAR`
```
Mode: REVERSE
Alert level: GREEN
Trigger: No obstacle detected within 3m

Visual:
  - Alert border: solid #22c55e (green), 4px, no pulse
  - Alert border glow: inset box-shadow with --pn-green-glow, 20px spread
  - Alert label: "CLEAR" on green pill (#22c55e background, white text)
  - Mode badge: "REVERSE" in green
  - Detection pills: all blue (inactive)
  - Speed: "0 km/h"
  - Confidence: "—"
  - Bounding boxes: none
  - Hazard card: hidden
  - Disconnect overlay: hidden
  - Info strip: LIVE (green), LOCKED (cyan), SYNCED (purple), 18ms (orange)

Camera canvas: Draw road scene — dark asphalt, lane markings, perspective lines. No objects.

Audio cue (text indicator only): Silent or single soft chime
```

### State: `REVERSE_APPROACHING`
```
Mode: REVERSE
Alert level: ORANGE
Trigger: Obstacle detected at 1–3m distance, OR moderate-speed approach

Visual:
  - Alert border: #f59e0b (orange), 4px, PULSING (opacity toggle every 600ms)
  - Alert border glow: inset box-shadow with --pn-orange-glow, 30px spread
  - Alert label: "SLOW DOWN" on orange pill
  - Mode badge: "REVERSE" in orange
  - Detection pills: VEH active (purple)
  - Speed: "3 km/h"
  - Confidence: "87%" in orange
  - Bounding boxes: 1x car at mid-distance, orange stroke, label "car 87%"
  - Hazard card: hidden

Camera canvas: Road + car object drawn at middle distance (y ~80-160)

Audio cue indicator: "~1Hz beep" text shown briefly
```

### State: `REVERSE_DANGER`
```
Mode: REVERSE
Alert level: RED
Trigger: Obstacle within 1m, OR fast approach

Visual:
  - Alert border: #ef4444 (red), 4px, FAST PULSING (opacity toggle every 250ms)
  - Alert border glow: inset box-shadow with --pn-red-glow, 40px spread
  - Alert label: "STOP" on red pill (slightly larger font: 14px)
  - Mode badge: "REVERSE" in red
  - Detection pills: VEH active (purple)
  - Speed: "2 km/h"
  - Confidence: "94%" in red
  - Bounding boxes: 1x car very close (large bbox, bottom of frame), red stroke, "car 94%"
  - Hazard card: hidden

Camera canvas: Road + large car object at close range (y ~140-230)

Audio cue indicator: "~4Hz ALARM" text pulsing
```

### State: `REVERSE_PERSON`
```
Mode: REVERSE
Alert level: RED (IMMEDIATE — this is the ethical value module in action)
Trigger: Person or animal detected at ANY distance

CRITICAL DESIGN RULE: Person/animal detection bypasses the green→orange→red progression.
ANY human at ANY distance = instant RED. This is hard-coded. This is the IP's ethical
value governing module demonstrated in practice. The cost of a false positive (annoying
beep when someone walks past 5m away) is trivial. The cost of a false negative
(silent green while backing into a child) is catastrophic.

Visual:
  - Alert border: #ef4444 (red), 4px, FAST PULSING (250ms)
  - Alert border glow: --pn-red-glow, 40px spread
  - Alert label: "⚠ PERSON — STOP" on red pill
  - Mode badge: "REVERSE" in red
  - Detection pills: HUM active (orange)
  - Speed: "1 km/h"
  - Confidence: "91%" in red
  - Bounding boxes: 1x person shape, red stroke, "person 91%"

Camera canvas: Road + person figure drawn

Audio cue indicator: "VOICE: STOP" text + continuous alarm indicator
```

### State: `REVERSE_POTHOLE`
```
Mode: REVERSE
Alert level: RED (border) but NO fast pulse — pothole is a hazard, not an imminent collision
Trigger: Pothole detected on road surface

Visual:
  - Alert border: #ef4444 (red), 4px, NO PULSE (solid)
  - Alert border glow: --pn-red-glow, 15px spread (subtle)
  - Alert label: "POTHOLE DETECTED" on red pill
  - Mode badge: "REVERSE" in green (mode itself is fine, it's the road that's bad)
  - Detection pills: POT active (red)
  - Speed: "1 km/h"
  - Confidence: "82%" in red
  - Bounding boxes: 1x elliptical bbox around pothole, red stroke, "pothole 82%"

Camera canvas: Road + pothole (dark ellipse on road surface)
```

### State: `DRIVING`
```
Mode: DRIVING
Alert level: MONITORING (cyan — distinct from reversing color language)
Trigger: GPS speed > 5 km/h

Visual:
  - Alert border: #22d3ee (cyan), 4px, solid (no pulse — don't distract the driver)
  - Alert border glow: cyan glow, 15px spread (very subtle)
  - Alert label: "MONITORING" on cyan pill
  - Mode badge: "DRIVING" in cyan
  - Detection pills: POT active (red), VEH active (purple)
  - Speed: "47 km/h"
  - Confidence: "76%" in cyan
  - Bounding boxes: 1x pothole + 1x car (both visible), pothole=red stroke, car=purple stroke
  - Hazard card: VISIBLE — "⚠ Pothole ahead — 120m" / "Reported 3x in last 7 days · Severity: High"

Camera canvas: Road + pothole at distance + car in adjacent lane

IMPORTANT: The hazard card shows a PREDICTIVE warning from the cloud map — this pothole
was reported by OTHER users. The camera hasn't seen it yet. This is the network value feature.
```

### State: `DISCONNECTED`
```
Mode: REVERSE (assumed — we don't know, camera is gone)
Alert level: GRAY — NEVER GREEN. This is the #1 safety design rule.
Trigger: Camera stream lost (WiFi drop, power loss, hardware failure)

CRITICAL DESIGN RULE: If the camera disconnects, the app MUST NOT show green.
Green means "safe to reverse." A disconnected camera means "we have no idea what's
behind you." The app shows a distinct gray state with a clear warning. The worst
possible failure mode for a safety product is reassuring the driver while blind.

Visual:
  - Alert border: #666666 (gray), 4px, solid
  - Alert border glow: none
  - Alert label: "NO SIGNAL" on gray pill
  - Mode badge: "REVERSE" in gray
  - Detection pills: all blue (inactive)
  - Speed: "0 km/h"
  - Confidence: "—" in gray
  - Bounding boxes: none
  - Hazard card: hidden
  - Disconnect overlay: VISIBLE — full camera area covered with:
    - Dark semi-transparent background (rgba(0,0,0,0.85))
    - Crossed-out circle icon (48px, gray)
    - "CAMERA DISCONNECTED" text (14px, gray, letter-spacing)
    - "Check Wi-Fi connection to PotholeNet-AP" subtext (11px, darker gray)
  - Info strip: STREAM shows "LOST" in red (all other indicators unchanged)

Camera canvas: Black (no feed)

Audio cue indicator: Distinct warning chime (different from reversing alerts)
```

---

## 4. CAMERA FEED — CANVAS RENDERING

The camera feed is a `<canvas>` element that draws a simulated rear-view road scene. It is NOT a video or image — it's procedurally drawn.

### Road drawing spec
```
Canvas size: 320 x 240 (scaled to fill container via CSS)
Background: #1a1a1a (dark asphalt)
Road surface: #2a2a2a (slightly lighter), extends from x=40 to x=280
Center line: Dashed white/gray line (#444), dash pattern 20on/15off
Road edges: Subtle converging lines from bottom-wider to top-narrower (perspective)
```

### Object drawing
Objects are simple geometric shapes — NOT photorealistic. This is a simulation.

**Car:** Filled rectangle with rounded corners, color #445 or #335. Small colored dots for headlights (yellow) and taillights (red). Size varies by distance:
- Far (approaching): ~50x80px at y=80
- Close (danger): ~60x90px at y=140
- Adjacent lane (driving): ~40x60px at y=60

**Pothole:** Dark ellipse (#0a0a0a) with gray stroke (#555). Inner darker ellipse for depth effect. ~36x16px.

**Person:** Simple stick figure — circle head (#ccc, r=6), rectangle torso (#888), rectangle arms, rectangle legs. ~20px wide, ~40px tall.

### Bounding boxes
Rendered as an SVG overlay on top of the canvas, with `viewBox="0 0 320 240"` and `preserveAspectRatio="none"` to match canvas coordinates.

Each bounding box:
- `<rect>` with 2px stroke, no fill, rx=2
- `<text>` label above the box: "[class] [confidence]%" in monospace 10px
- Stroke color matches alert level (green=safe, orange=approaching, red=danger, purple=vehicle in driving mode)

---

## 5. INTERACTIVE ELEMENTS

### Bottom navigation bar
5 buttons in a row, evenly spaced:

| Button | Icon | Action (in demo) | Style |
|--------|------|-------------------|-------|
| Servo Left | `ChevronLeft` | Visual feedback only (flash border) | 1px #333 border, 8px radius |
| Report Hazard | `AlertTriangle` | Show brief "Report submitted" toast | 2px #ef4444 border, circular 48px, red icon |
| Center Camera | `Crosshair` | Visual feedback only | 1px #333 border |
| Map View | `Map` | Show brief "Map view coming soon" toast | 1px #333 border |
| Servo Right | `ChevronRight` | Visual feedback only | 1px #333 border |

### Demo controls (below the phone frame — for presenter use only)
Row of buttons that switch between the 7 states. These are NOT part of the app UI — they're for the person giving the demo to quickly switch scenes.

Label each button clearly: "Safe" / "Approaching" / "Danger" / "Person" / "Pothole" / "Driving" / "Disconnected"

Style: small, subtle, below the phone frame. Don't make them look like part of the app.

### Auto-demo mode
Add a "Play Demo" button that auto-cycles through states in this order with 3-second pauses:
1. REVERSE_CLEAR (3s)
2. REVERSE_APPROACHING (3s)
3. REVERSE_DANGER (3s)
4. REVERSE_CLEAR (2s)
5. REVERSE_PERSON (3s)
6. REVERSE_POTHOLE (3s)
7. DRIVING (4s)
8. DISCONNECTED (3s)
9. REVERSE_CLEAR (return to start)

This is for the pitch — the presenter can hit "Play Demo" and talk over the auto-cycling states.

---

## 6. ANIMATIONS — EXACT SPECIFICATIONS

### Alert border pulse
```css
/* Orange pulse — approaching state */
@keyframes pulse-orange {
  0%, 100% { border-color: #f59e0b; }
  50% { border-color: transparent; }
}
.pulse-orange { animation: pulse-orange 1.2s ease-in-out infinite; }

/* Red pulse — danger/person state (faster) */
@keyframes pulse-red {
  0%, 100% { border-color: #ef4444; }
  50% { border-color: transparent; }
}
.pulse-red { animation: pulse-red 0.5s ease-in-out infinite; }
```

### State transitions
Use Framer Motion `AnimatePresence` for:
- Alert label text changes (fade out old → fade in new, 200ms)
- Hazard card appearance (slide up + fade in, 300ms)
- Disconnect overlay (fade in, 400ms)
- Bounding box appearances (scale from 0.8 → 1.0 + fade in, 200ms)

### Mode badge
Subtle background pulse when mode changes (REVERSE → DRIVING or vice versa). Brief scale to 1.1 then back to 1.0 over 300ms.

---

## 7. INFO STRIP — TELEMETRY BAR

Horizontal bar below the camera feed. 4 columns, evenly spaced, center-aligned.

| Column | Label | Value | Color |
|--------|-------|-------|-------|
| STREAM | "STREAM" (9px, muted) | "LIVE" or "LOST" | Green if live, Red if lost |
| GPS | "GPS" (9px, muted) | "LOCKED" | Cyan always (simulated) |
| CLOUD | "CLOUD" (9px, muted) | "SYNCED" | Purple always (simulated) |
| INFER | "INFER" (9px, muted) | "18ms" (randomize 15-25ms) | Orange always |

Value font: monospace, 12px, weight 500. Label font: sans-serif, 9px, muted.

---

## 8. WHAT NOT TO DO — ANTI-PATTERNS

These are mistakes from a previous prompt. Do NOT implement any of these:

1. **NO rainbow gradient animation.** No flowing hue rotations. No disco effects. This is a safety app for real drivers, not a music visualizer.

2. **NO Tron/cyberpunk/neon aesthetic.** No glow effects, no neon borders, no sci-fi styling. The app should look like a clean, professional automotive safety tool.

3. **NO CarPlay or tablet layouts.** This is a phone-only demo. One layout. Don't waste time on responsive breakpoints.

4. **NO swipe gestures for core functionality.** Buttons only. A driver reversing their car is not going to swipe. Tap targets must be large and obvious.

5. **NO localStorage or sessionStorage.** Not supported in the demo environment.

6. **NO real API calls.** Everything is simulated. No WebSocket connections, no fetch calls to backends that don't exist.

7. **NO over-engineering the state management.** useState is fine. This is a demo with 7 states, not a production app with complex async flows.

8. **NO sound files.** Show text indicators for audio cues ("~1Hz BEEP", "ALARM", "VOICE: STOP"). Judges will understand the concept without actual audio in a demo.

9. **NO automatic camera rotation or servo automation.** Servo buttons are manual — the user taps left/right/center. No automatic panning.

10. **NO claiming the system is autonomous.** Every piece of text in the UI must reinforce that this is an ASSISTIVE system. The driver decides. The AI informs.

---

## 9. DEMO PRESENTATION FEATURES

### Title bar (above the phone frame)
Show "PotholeNet" logo text + tagline: "Crowdsourced Road Hazard Intelligence"
Style: clean, professional, small. Not part of the phone UI.

### Current state description (below demo controls)
Show a 1-line description of what the current state demonstrates:
- Safe: "No obstacles detected — green means clear to reverse"
- Approaching: "Vehicle detected at 1-3m — beep cadence increases"
- Danger: "Vehicle within 1m — immediate stop warning"
- Person: "Person detected at ANY distance — instant red (ethical value module)"
- Pothole: "Pothole detected on road surface — hazard alert"
- Driving: "Driving mode — predictive warning from crowdsourced map"
- Disconnected: "Camera feed lost — NEVER shows false green"

This helps the judge understand what they're seeing during the demo.

### IP alignment callout
When in PERSON state, show a subtle callout below the phone:
"⚡ IP Pillar: Ethical Value Module — person/animal detection bypasses distance thresholds"

When in DRIVING state with hazard card:
"⚡ IP Pillar: Cloud AI + Adaptive Learning — predictive warning from crowdsourced data"

When in DISCONNECTED state:
"⚡ IP Pillar: Value-Driven Decisions — system fails visibly, never silently"

---

## 10. BUILD AND RUN

```bash
# Setup
npm create vite@latest potholenet-demo -- --template react-ts
cd potholenet-demo
npm install tailwindcss @tailwindcss/vite framer-motion lucide-react
npm run dev
```

The app should:
- Start on localhost:5173
- Show the phone frame centered on a dark/neutral background
- Default to REVERSE_CLEAR state
- Be fully controllable via the demo buttons below the phone
- Auto-demo mode available with one click
- Look professional enough that a judge thinks "this is a real product"

---

## 11. ACCEPTANCE CRITERIA — HOW TO KNOW IT'S DONE

The build is complete when:

- [ ] All 7 states render correctly with the exact colors, animations, and layouts specified
- [ ] State transitions are smooth (Framer Motion, 200-300ms)
- [ ] Camera canvas draws the road scene with objects for each state
- [ ] Bounding boxes appear correctly over detected objects
- [ ] Alert border pulses at the correct speed for orange (600ms) and red (250ms)
- [ ] Disconnect state shows gray, NEVER green
- [ ] Person state goes straight to red regardless of distance
- [ ] Driving mode shows the predictive hazard card
- [ ] Info strip shows correct telemetry values
- [ ] Demo controls switch states reliably
- [ ] Auto-demo cycles through all states with correct timing
- [ ] IP alignment callouts appear for the 3 key states
- [ ] No console errors, no broken layouts, no missing elements
- [ ] Looks like a real product, not a student project

---

*This document is the single source of truth. If anything in the codebase contradicts this spec, the spec wins.*
