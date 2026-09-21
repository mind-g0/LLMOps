import { useEffect, useState } from "react";
import { checkHealth } from "@/api/client";

export type ApiStatus = "checking" | "online" | "offline";

export function useApiStatus(pollMs = 30000): ApiStatus {
  const [status, setStatus] = useState<ApiStatus>("checking");

  useEffect(() => {
    let cancelled = false;
    const controller = new AbortController();

    async function check() {
      const ok = await checkHealth(controller.signal);
      if (!cancelled) {
        setStatus(ok ? "online" : "offline");
      }
    }

    check();
    const interval = setInterval(check, pollMs);
    return () => {
      cancelled = true;
      controller.abort();
      clearInterval(interval);
    };
  }, [pollMs]);

  return status;
}
