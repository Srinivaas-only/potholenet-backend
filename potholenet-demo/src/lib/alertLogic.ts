import type { AppScene, Detection } from "../types";

const HUMAN_CLASSES = ["person", "dog", "cat"];
const VEHICLE_CLASSES = ["car", "truck", "motorcycle", "bicycle", "bus"];

export function isHumanDetection(label: string): boolean {
  return HUMAN_CLASSES.includes(label);
}

export function isVehicleDetection(label: string): boolean {
  return VEHICLE_CLASSES.includes(label);
}

export function deriveAlertState(
  detections: Detection[],
  gpsSpeedKmh: number,
  cameraConnected: boolean
): AppScene {
  if (!cameraConnected) return "DISCONNECTED";
  if (gpsSpeedKmh > 5) return "DRIVING";
  if (detections.some((d) => d.isHuman)) return "PERSON";
  if (detections.some((d) => d.label === "pothole")) return "POTHOLE";
  const vehicles = detections.filter((d) => d.isVehicle);
  if (vehicles.length > 0) {
    const largestArea = Math.max(...vehicles.map((d) => d.bbox[2] * d.bbox[3]));
    if (largestArea > 25000) return "DANGER";
    if (largestArea > 8000) return "APPROACHING";
  }
  return "CLEAR";
}