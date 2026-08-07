import { useEffect, useRef, useState } from "react";
import { api } from "../lib/api";

// Subscribes to /ws/scans/{scan_id} for the lifetime of the component and
// keeps a rolling event log plus the most recent event of each type, so a
// page can both render a timeline and react to specific events (e.g.
// invalidate a query when scan.completed arrives).
export function useScanSocket(scanId, { onEvent } = {}) {
  const [events, setEvents] = useState([]);
  const [connected, setConnected] = useState(false);
  const onEventRef = useRef(onEvent);
  onEventRef.current = onEvent;

  useEffect(() => {
    if (!scanId) return undefined;
    setConnected(true);

    const unsubscribe = api.connectScanSocket(scanId, (message) => {
      setEvents((prev) => [...prev, message].slice(-200));
      onEventRef.current?.(message);
    });

    return () => {
      setConnected(false);
      unsubscribe?.();
    };
  }, [scanId]);

  return { events, connected };
}
