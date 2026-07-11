/**
 * WebSocket sync hook — real-time commitment updates (OL-003).
 *
 * Connects to /v1/ws/{context_id}, receives DeltaEvents,
 * and invalidates TanStack Query cache on changes.
 */

import { useEffect, useRef } from "react";
import { useQueryClient } from "@tanstack/react-query";

const WS_BASE = (import.meta.env.VITE_API_URL ?? "http://localhost:8000/v1")
  .replace("http://", "ws://")
  .replace("https://", "wss://");

interface DeltaEvent {
  event: string;
  context_id: string;
  subject_id: string;
  seq: number;
  data: Record<string, unknown>;
}

export function useContextSync(contextId: string | null): void {
  const queryClient = useQueryClient();
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!contextId) return;

    const url = `${WS_BASE}/ws/${contextId}`;
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onmessage = (event) => {
      const delta: DeltaEvent = JSON.parse(event.data as string);

      // Invalidate commitment queries to pick up changes
      if (
        delta.event === "commitment_created" ||
        delta.event === "commitment_updated" ||
        delta.event === "state_changed"
      ) {
        void queryClient.invalidateQueries({ queryKey: ["commitments"] });
      }
    };

    ws.onclose = () => {
      wsRef.current = null;
    };

    // Keepalive ping every 30s
    const pingInterval = setInterval(() => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send("ping");
      }
    }, 30_000);

    return () => {
      clearInterval(pingInterval);
      ws.close();
      wsRef.current = null;
    };
  }, [contextId, queryClient]);
}
