import { useEffect, useRef } from "react";

export function useWakeLock(active: boolean) {
  const sentinel = useRef<WakeLockSentinel | null>(null);

  useEffect(() => {
    if (!active || !("wakeLock" in navigator)) return;

    const request = async () => {
      try {
        sentinel.current = await navigator.wakeLock.request("screen");
      } catch (e) {
        console.warn("Wake lock failed", e);
      }
    };

    request();

    // Re-request on visibility change (e.g., after tab switch)
    const onVisChange = () => {
      if (document.visibilityState === "visible") request();
    };
    document.addEventListener("visibilitychange", onVisChange);

    return () => {
      document.removeEventListener("visibilitychange", onVisChange);
      sentinel.current?.release();
      sentinel.current = null;
    };
  }, [active]);
}