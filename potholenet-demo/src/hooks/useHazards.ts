import { useState, useEffect, useRef } from "react";
import { getHazards } from "../lib/api";
import type { HazardItem } from "../lib/api";

/**
 * Polls GET /hazards every 5 seconds using GPS coords.
 * Falls back gracefully if no GPS or backend is unreachable.
 */
export function useHazards(
  gpsCoords: { lat: number; lng: number } | null,
  enabled: boolean = true
) {
  const [hazards, setHazards] = useState<HazardItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (!enabled || !gpsCoords) {
      setHazards([]);
      return;
    }

    let mounted = true;

    const fetchHazards = async () => {
      if (!gpsCoords) return;
      setLoading(true);
      try {
        const result = await getHazards(gpsCoords.lat, gpsCoords.lng, 2000, 1);
        if (mounted) {
          setHazards(result.hazards);
          setError(null);
        }
      } catch (err: any) {
        if (mounted) setError(err.message || "Failed to fetch hazards");
      } finally {
        if (mounted) setLoading(false);
      }
    };

    // Initial fetch
    fetchHazards();

    // Poll every 5 seconds
    intervalRef.current = setInterval(fetchHazards, 5000);

    return () => {
      mounted = false;
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [gpsCoords?.lat, gpsCoords?.lng, enabled]);

  const nearbyCount = hazards.length;

  return { hazards, nearbyCount, loading, error };
}