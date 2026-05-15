import { useEffect, useRef } from "react";
import type { AppScene } from "../types";

export function useVibration(scene: AppScene, enabled: boolean) {
  const prev = useRef<AppScene>(scene);
  useEffect(() => {
    if (!enabled || !navigator.vibrate || scene === prev.current) return;
    prev.current = scene;
    switch (scene) {
      case "PERSON": navigator.vibrate([200, 80, 200, 80, 200]); break;
      case "DANGER": navigator.vibrate([150, 60, 150, 60, 150]); break;
      case "POTHOLE": navigator.vibrate([120, 40, 120]); break;
      case "APPROACHING": navigator.vibrate(80); break;
    }
  }, [scene, enabled]);
}