import { useState, useEffect, useRef } from "react";
import type { RefObject } from "react";
import type { Detection } from "../types";
import { isHumanDetection, isVehicleDetection } from "../lib/alertLogic";
import { detectDualMode } from "../lib/api";

type MediaElement = HTMLImageElement | HTMLVideoElement;

export function useDetection(
  mediaRef: RefObject<MediaElement | null>,
  enabled: boolean,
  threshold: number = 0.5,
  useBackend: boolean = true,
  gpsSpeed: number = 0
) {
  const [detections, setDetections] = useState<Detection[]>([]);
  const [inferenceMs, setInferenceMs] = useState(0);
  const [modelLoaded, setModelLoaded] = useState(false);
  const modelRef = useRef<any>(null);

  // ── Local TF.js model loading (fallback) ──
  useEffect(() => {
    if (!enabled) return;

    let mounted = true;
    const loadModel = async () => {
      try {
        const tf = await import("@tensorflow/tfjs");
        await tf.ready();
        const cocoSsd = await import("@tensorflow-models/coco-ssd");
        const model = await cocoSsd.load({ base: "lite_mobilenet_v2" });
        if (mounted) {
          modelRef.current = model;
          setModelLoaded(true);
        }
      } catch (err) {
        console.warn("TF.js model load failed:", err);
        // If backend mode is on, we don't need TF.js
        if (useBackend && mounted) {
          setModelLoaded(true);
        }
      }
    };
    loadModel();
    return () => { mounted = false; };
  }, [enabled]);

  // ── Canvas for capturing frames to send to backend ──
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  const getCanvas = (): HTMLCanvasElement => {
    if (!canvasRef.current) {
      canvasRef.current = document.createElement("canvas");
      canvasRef.current.width = 640;
      canvasRef.current.height = 480;
    }
    return canvasRef.current;
  };

  const captureFrame = (el: MediaElement): Blob | null => {
    const canvas = getCanvas();
    const ctx = canvas.getContext("2d");
    if (!ctx) return null;

    try {
      let w: number, h: number;
      if (el instanceof HTMLImageElement) {
        w = el.naturalWidth || 640;
        h = el.naturalHeight || 480;
      } else {
        w = el.videoWidth || 640;
        h = el.videoHeight || 480;
      }
      canvas.width = w;
      canvas.height = h;
      ctx.drawImage(el, 0, 0, w, h);

      return new Promise<Blob | null>((resolve) => {
        canvas.toBlob((blob) => resolve(blob), "image/jpeg", 0.8);
      }) as unknown as Blob | null;
    } catch {
      return null;
    }
  };

  // ── Detection loop ──
  useEffect(() => {
    if (!enabled || !modelLoaded) return;

    let stopped = false;

    const isReady = (el: MediaElement): boolean => {
      if (el instanceof HTMLImageElement) {
        return el.complete && el.naturalWidth > 0;
      }
      return el.readyState >= 2 && el.videoWidth > 0;
    };

    // ── Backend detection path ──
    const backendLoop = async () => {
      if (stopped) return;
      const el = mediaRef.current;

      if (el && isReady(el)) {
        try {
          // Capture frame to blob
          const canvas = getCanvas();
          const ctx = canvas.getContext("2d");
          if (!ctx) { setTimeout(backendLoop, 200); return; }

          let w: number, h: number;
          if (el instanceof HTMLImageElement) {
            w = el.naturalWidth || 640;
            h = el.naturalHeight || 480;
          } else {
            w = el.videoWidth || 640;
            h = el.videoHeight || 480;
          }
          canvas.width = w;
          canvas.height = h;
          ctx.drawImage(el, 0, 0, w, h);

          const blob = await new Promise<Blob | null>((resolve) => {
            canvas.toBlob((b) => resolve(b), "image/jpeg", 0.8);
          });

          if (blob && !stopped) {
            const start = performance.now();
            const result = await detectDualMode(blob, gpsSpeed);
            const elapsed = Math.round(performance.now() - start);
            if (!stopped) {
              setInferenceMs(elapsed);

              // Convert backend response to Detection[] format
              const filtered: Detection[] = [];

              // Add human detections
              for (const d of result.humans.details) {
                filtered.push({
                  label: d.label || "person",
                  confidence: Math.round(d.confidence),
                  bbox: [0, 0, 0, 0],
                  isHuman: true,
                  isVehicle: false,
                });
              }
              // Add vehicle detections
              for (const d of result.vehicles.details) {
                filtered.push({
                  label: d.label || "vehicle",
                  confidence: Math.round(d.confidence),
                  bbox: [0, 0, 0, 0],
                  isHuman: false,
                  isVehicle: true,
                });
              }
              // Add animal detections
              for (const d of result.animals.details) {
                filtered.push({
                  label: d.label || "animal",
                  confidence: Math.round(d.confidence),
                  bbox: [0, 0, 0, 0],
                  isHuman: false,
                  isVehicle: false,
                });
              }

              // Add pothole as a special detection (for scene logic)
              if (result.pothole.detected) {
                for (const d of result.pothole.details) {
                  filtered.push({
                    label: "pothole",
                    confidence: Math.round(d.confidence),
                    bbox: [d.x || 0, d.y || 0, d.width || 0, d.height || 0],
                    isHuman: false,
                    isVehicle: false,
                  });
                }
              }

              if (!stopped) setDetections(filtered);
            }
          }
        } catch (err) {
          // Backend unreachable — fall through to local detection on next tick
          console.warn("Backend detection failed, will retry:", err);
        }
      }

      // ~3 FPS for backend (saves bandwidth)
      if (!stopped) setTimeout(backendLoop, 333);
    };

    // ── Local TF.js detection path (fallback) ──
    const VALID = ["person", "car", "truck", "motorcycle", "bicycle", "bus", "dog", "cat"];
    const localLoop = async () => {
      if (stopped) return;
      const el = mediaRef.current;
      const model = modelRef.current;

      if (el && model && isReady(el)) {
        try {
          const start = performance.now();
          const preds = await model.detect(el);
          setInferenceMs(Math.round(performance.now() - start));

          const filtered: Detection[] = preds
            .filter((p: any) => p.score > threshold && VALID.includes(p.class))
            .map((p: any) => ({
              label: p.class,
              confidence: Math.round(p.score * 100),
              bbox: p.bbox as [number, number, number, number],
              isHuman: isHumanDetection(p.class),
              isVehicle: isVehicleDetection(p.class),
            }));

          if (!stopped) setDetections(filtered);
        } catch {
          // inference error — skip frame
        }
      }

      // ~5 FPS for local
      setTimeout(localLoop, 200);
    };

    if (useBackend) {
      backendLoop();
    } else {
      localLoop();
    }

    return () => { stopped = true; };
  }, [mediaRef, enabled, modelLoaded, threshold, useBackend, gpsSpeed]);

  return { detections, inferenceMs, modelLoaded };
}