/**
 * PotholeNet API Service Layer
 * All backend communication goes through here.
 */

const getBackendUrl = (): string => {
  try {
    const saved = localStorage.getItem("potholenet:settings");
    if (saved) {
      const parsed = JSON.parse(saved);
      if (parsed.backendUrl) return parsed.backendUrl.replace(/\/$/, "");
    }
  } catch {}
  return "http://localhost:8000";
};

// ============================================
// TYPES
// ============================================

export interface DetectionCategory {
  detected: boolean;
  count: number;
  details: Array<{ confidence: number; label?: string; x?: number; y?: number; width?: number; height?: number }>;
}

export interface DetectionResponse {
  pothole: DetectionCategory;
  humans: DetectionCategory;
  vehicles: DetectionCategory;
  animals: DetectionCategory;
  alert: string;
}

export interface DualModeDetectionResponse extends DetectionResponse {
  mode: string;
  velocity_kmh: number | null;
}

export interface ReportPayload {
  latitude: number;
  longitude: number;
  confidence: number;
  vehicle_type: "car" | "motorcycle" | "truck" | "bicycle";
  speed_kmh?: number;
  thumbnail_base64?: string;
}

export interface ReportResponse {
  report_id: string;
  latitude: number;
  longitude: number;
  severity_score: number;
  first_reported: string;
  last_seen: string;
  is_new: boolean;
}

export interface HazardItem {
  report_id: string;
  latitude: number;
  longitude: number;
  severity_score: number;
  distance_m: number;
  last_seen: string;
}

export interface HazardResponse {
  hazards: HazardItem[];
  count: number;
  query: { lat: number; lng: number; radius_m: number };
}

export interface HealthResponse {
  status: string;
  models_loaded: { pothole: boolean; yolov8: boolean };
  reports_count: number;
  uptime_seconds: number;
}

export interface FalseNegativeResponse {
  contribution_id: string;
  images_received: number;
  message: string;
}

// ============================================
// API CALLS
// ============================================

/** POST /detect — Run ML detection on an image */
export async function detectImage(imageBlob: Blob): Promise<DetectionResponse> {
  const url = getBackendUrl();
  const formData = new FormData();
  formData.append("image", imageBlob, "capture.jpg");

  const res = await fetch(`${url}/detect`, { method: "POST", body: formData });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Detection failed" }));
    throw new Error(err.detail || `Detection error ${res.status}`);
  }
  return res.json();
}

/** POST /detect/dual-mode — Dual-mode detection with speed context */
export async function detectDualMode(
  imageBlob: Blob,
  velocityKmh?: number
): Promise<DualModeDetectionResponse> {
  const url = getBackendUrl();
  const formData = new FormData();
  formData.append("image", imageBlob, "frame.jpg");

  const params = new URLSearchParams();
  if (velocityKmh !== undefined && velocityKmh !== null) {
    params.set("velocity_kmh", String(velocityKmh));
  }
  const query = params.toString() ? `?${params.toString()}` : "";

  const res = await fetch(`${url}/detect/dual-mode${query}`, {
    method: "POST",
    body: formData,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Detection failed" }));
    throw new Error(err.detail || `Detection error ${res.status}`);
  }
  return res.json();
}

/** POST /reports — Submit a pothole sighting */
export async function submitReport(payload: ReportPayload): Promise<ReportResponse> {
  const url = getBackendUrl();
  const res = await fetch(`${url}/reports`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Report failed" }));
    throw new Error(err.detail || `Report error ${res.status}`);
  }
  return res.json();
}

/** GET /hazards — Query hazards near a location */
export async function getHazards(
  lat: number,
  lng: number,
  radiusM: number = 2000,
  minSeverity: number = 1
): Promise<HazardResponse> {
  const url = getBackendUrl();
  const params = new URLSearchParams({
    lat: String(lat),
    lng: String(lng),
    radius_m: String(radiusM),
    min_severity: String(minSeverity),
  });

  const res = await fetch(`${url}/hazards?${params}`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Hazard query failed" }));
    throw new Error(err.detail || `Hazard error ${res.status}`);
  }
  return res.json();
}

/** GET /health — Check server health */
export async function checkHealth(): Promise<HealthResponse> {
  const url = getBackendUrl();
  const res = await fetch(`${url}/health`, { signal: AbortSignal.timeout(5000) });
  if (!res.ok) throw new Error(`Health check failed: ${res.status}`);
  return res.json();
}

/** POST /reports/false-negative — Submit missed pothole frames */
export async function submitFalseNegative(
  latitude: number,
  longitude: number,
  images: Blob[]
): Promise<FalseNegativeResponse> {
  const url = getBackendUrl();
  const formData = new FormData();
  formData.append("latitude", String(latitude));
  formData.append("longitude", String(longitude));
  images.forEach((img, i) => {
    formData.append("images", img, `frame_${i}.jpg`);
  });

  const res = await fetch(`${url}/reports/false-negative`, {
    method: "POST",
    body: formData,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Submission failed" }));
    throw new Error(err.detail || `False negative error ${res.status}`);
  }
  return res.json();
}

/** POST /location/update — Push GPS to backend */
export async function updateLocation(data: {
  latitude: number;
  longitude: number;
  accuracy_m?: number;
  speed_kmh?: number;
  bearing?: number;
}): Promise<{ status: string }> {
  const url = getBackendUrl();
  try {
    const res = await fetch(`${url}/location/update`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    if (!res.ok) throw new Error();
    return res.json();
  } catch {
    return { status: "error" };
  }
}