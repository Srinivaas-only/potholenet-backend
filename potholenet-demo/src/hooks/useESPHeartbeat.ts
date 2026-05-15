import { useState, useEffect } from "react";
import { checkHeartbeat } from "../lib/esp32";

export function useESPHeartbeat(baseUrl: string, enabled: boolean) {
  const [connected, setConnected] = useState(false);
  const [espInfo, setEspInfo] = useState<{ uptime: number; clients: number } | null>(null);

  useEffect(() => {
    if (!enabled) {
      setConnected(false);
      return;
    }

    let fails = 0;
    let mounted = true;

    const check = async () => {
      const result = await checkHeartbeat(baseUrl);
      if (!mounted) return;

      if (result.alive) {
        fails = 0;
        setConnected(true);
        setEspInfo({ uptime: result.uptime ?? 0, clients: result.clients ?? 0 });
      } else {
        fails++;
        if (fails >= 3) {
          setConnected(false);
          setEspInfo(null);
        }
      }
    };

    check();
    const iv = setInterval(check, 2000);
    return () => {
      mounted = false;
      clearInterval(iv);
    };
  }, [baseUrl, enabled]);

  return { connected, espInfo };
}