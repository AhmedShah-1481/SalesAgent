import { API_URL } from "@/lib/api";
import type { ActivityEvent } from "@/types/pipeline";

/**
 * Subscribe to the backend's live activity feed (SSE, event name "activity").
 * Returns an unsubscribe function. No-op during SSR (EventSource is browser-only).
 */
export function subscribeActivity(
  onEvent: (event: ActivityEvent) => void,
  onStatus?: (connected: boolean) => void,
): () => void {
  if (typeof window === "undefined" || typeof EventSource === "undefined") {
    return () => {};
  }
  const es = new EventSource(`${API_URL}/activity/stream`);
  es.addEventListener("open", () => onStatus?.(true));
  es.addEventListener("error", () => onStatus?.(false));
  es.addEventListener("activity", (e) => {
    try {
      onEvent(JSON.parse((e as MessageEvent).data) as ActivityEvent);
    } catch {
      /* ignore a malformed frame */
    }
  });
  return () => es.close();
}
