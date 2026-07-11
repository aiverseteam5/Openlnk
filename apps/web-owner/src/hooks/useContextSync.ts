/**
 * WebSocket sync hook — real-time commitment updates (OL-003).
 *
 * Connects to /v1/ws/{context_id}, receives DeltaEvents,
 * and invalidates TanStack Query cache on changes.
 * Reconnects with exponential backoff on disconnect.
 */

import { useEffect, useRef, useCallback } from "react";
import { useQueryClient } from "@tanstack/react-query";

const WS_BASE = (import.meta.env.VITE_API_URL ?? "http://localhost:8000/v1")
  .replace("http://", "ws://")
  .replace("https://", "wss://");

const MAX_RECONNECT_DELAY = 30_000;
const INITIAL_RECONNECT_DELAY = 1_000;

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
  const reconnectDelay = useRef(INITIAL_RECONNECT_DELAY);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const unmounted = useRef(false);

  const connect = useCallback(
    (ctxId: string) => {
      if (unmounted.current) return;

      const url = `${WS_BASE}/ws/${ctxId}`;
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        reconnectDelay.current = INITIAL_RECONNECT_DELAY;
      };

      ws.onmessage = (event) => {
        const delta: DeltaEvent = JSON.parse(event.data as string);

        if (
          delta.event === "commitment_created" ||
          delta.event === "commitment_updated" ||
          delta.event === "state_changed"
        ) {
          void queryClient.invalidateQueries({ queryKey: ["commitments"] });
          void queryClient.invalidateQueries({
            queryKey: ["commitment", delta.subject_id],
          });
        }
      };

      ws.onclose = () => {
        wsRef.current = null;
        if (unmounted.current) return;

        // Exponential backoff reconnect
        reconnectTimer.current = setTimeout(() => {
          reconnectDelay.current = Math.min(
            reconnectDelay.current * 2,
            MAX_RECONNECT_DELAY,
          );
          connect(ctxId);
        }, reconnectDelay.current);
      };

      ws.onerror = () => {
        ws.close();
      };
    },
    [queryClient],
  );

  useEffect(() => {
    unmounted.current = false;

    if (!contextId) return;

    connect(contextId);

    // Keepalive ping every 30s
    const pingInterval = setInterval(() => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send("ping");
      }
    }, 30_000);

    return () => {
      unmounted.current = true;
      clearInterval(pingInterval);
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
      wsRef.current?.close();
      wsRef.current = null;
    };
  }, [contextId, connect]);
}
