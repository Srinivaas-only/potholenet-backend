import { useState, useEffect, useRef } from "react";
import type { RefObject } from "react";
import type { Detection } from "../types";
import { isHumanDetection, isVehicleDetection } from "../lib/alertLogic";

type MediaElement = HTMLImageElement | HTMLVideoElement;

export function useDetection(
  mediaRef: RefObject<MediaElement | null>,
  enabled: boolean,
  threshold: number = 0.5
) {
  const [detections, setDetections] = useState<Detection[]>([]);
  const [inferenceMs, setInferenceMs] = useState(0);
  const [modelLoaded, setModelLoaded] = useState(false);
  const modelRef = useRef<any>(null);

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
      }
    };
    loadModel();
    return () => { mounted = false; };
  }, [enabled]);

  useEffect(() => {
    if (!enabled || !modelLoaded) return;

    let stopped = false;
    const VALID = ["person", "car", "truck", "motorcycle", "bicycle", "bus", "dog", "cat"];

    const isReady = (el: MediaElement): boolean => {
      if (el instanceof HTMLImageElement) {
        return el.complete && el.naturalWidth > 0;
      }
      // HTMLVideoElement
      return el.readyState >= 2 && el.videoWidth > 0;
    };

    const loop = async () => {
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

      // ~5 FPS to keep phone cool
      setTimeout(loop, 200);
    };

    loop();
    return () => { stopped = true; };
  }, [mediaRef, enabled, modelLoaded, threshold]);

  return { detections, inferenceMs, modelLoaded };
}