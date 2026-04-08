import { useCallback, useEffect, useRef } from "react";

export interface WsDirectMessagePayload {
  id: string;
  from_user_id: string;
  to_user_id: string;
  body: string;
  created_at: string;
}

function buildWsUrl(token: string): string {
  const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${proto}//${window.location.host}/ws/social?token=${encodeURIComponent(token)}`;
}

export function useSocialWebSocket(
  token: string | null,
  handlers: {
    onDm?: (message: WsDirectMessagePayload) => void;
    onConnectionStateChanged?: () => void;
    onWsError?: (detail: string) => void;
  },
) {
  const wsRef = useRef<WebSocket | null>(null);
  const handlersRef = useRef(handlers);
  handlersRef.current = handlers;

  useEffect(() => {
    if (!token) return;

    const ws = new WebSocket(buildWsUrl(token));
    wsRef.current = ws;

    ws.onmessage = (ev) => {
      try {
        const data = JSON.parse(ev.data as string) as {
          type?: string;
          message?: WsDirectMessagePayload;
          detail?: string;
        };
        if (data.type === "dm" && data.message) {
          handlersRef.current.onDm?.(data.message);
        }
        if (data.type === "connection_state_changed") {
          handlersRef.current.onConnectionStateChanged?.();
        }
        if (data.type === "error" && typeof data.detail === "string") {
          handlersRef.current.onWsError?.(data.detail);
        }
      } catch {
        /* ignore malformed */
      }
    };

    const ping = window.setInterval(() => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: "ping" }));
      }
    }, 40_000);

    return () => {
      window.clearInterval(ping);
      ws.close();
      wsRef.current = null;
    };
  }, [token]);

  const sendDm = useCallback((toUserId: string, text: string) => {
    const ws = wsRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN) {
      handlersRef.current.onWsError?.("Chat connection lost. Refresh the page.");
      return;
    }
    ws.send(JSON.stringify({ type: "dm", to_user_id: toUserId, text }));
  }, []);

  return { sendDm };
}
