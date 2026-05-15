import { useState, useEffect } from "react";

export function useGPS(enabled: boolean) {
  const [speed, setSpeed] = useState(0); // km/h
  const [coords, setCoords] = useState<{ lat: number; lng: number } | null>(null);
  const [gpsStatus, setGpsStatus] = useState<"idle" | "acquiring" | "locked" | "denied">("idle");

  useEffect(() => {
    if (!enabled || !navigator.geolocation) {
      setGpsStatus("denied");
      return;
    }

    setGpsStatus("acquiring");
    const watchId = navigator.geolocation.watchPosition(
      (pos) => {
        setGpsStatus("locked");
        setCoords({ lat: pos.coords.latitude, lng: pos.coords.longitude });
        // speed comes in m/s, convert to km/h
        const kmh = pos.coords.speed != null ? pos.coords.speed * 3.6 : 0;
        setSpeed(Math.round(kmh));
      },
      () => {
        setGpsStatus("denied");
      },
      { enableHighAccuracy: true, maximumAge: 1000, timeout: 5000 }
    );

    return () => navigator.geolocation.clearWatch(watchId);
  }, [enabled]);

  return { speed, coords, gpsStatus };
}