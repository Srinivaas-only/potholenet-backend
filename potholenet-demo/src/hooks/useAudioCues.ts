import { useEffect, useRef } from "react";
import type { AppScene } from "../types";

export function useAudioCues(scene: AppScene, soundsEnabled: boolean, voiceCuesEnabled: boolean) {
  const prevScene = useRef<AppScene>(scene);
  const audioCtxRef = useRef<AudioContext | null>(null);

  const beep = (freq: number, duration: number, vol: number) => {
    try {
      if (!audioCtxRef.current) audioCtxRef.current = new AudioContext();
      const ctx = audioCtxRef.current;
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.frequency.value = freq;
      gain.gain.value = vol;
      osc.start();
      osc.stop(ctx.currentTime + duration / 1000);
    } catch {}
  };

  useEffect(() => {
    if (!soundsEnabled || scene === prevScene.current) return;
    prevScene.current = scene;

    if (voiceCuesEnabled) {
      try {
        const msgs: Partial<Record<AppScene, string>> = {
          PERSON: "Person detected! Stop!",
          POTHOLE: "Pothole detected!",
          DANGER: "Danger! Vehicle very close!",
          APPROACHING: "Vehicle approaching.",
        };
        if (msgs[scene]) {
          const u = new SpeechSynthesisUtterance(msgs[scene]);
          u.rate = 1.2;
          speechSynthesis.cancel();
          speechSynthesis.speak(u);
          return;
        }
      } catch {}
    }

    switch (scene) {
      case "PERSON":
      case "DANGER": beep(880, 150, 0.3); break;
      case "POTHOLE": beep(660, 120, 0.25); break;
      case "APPROACHING": beep(520, 100, 0.15); break;
    }
  }, [scene, soundsEnabled, voiceCuesEnabled]);
}