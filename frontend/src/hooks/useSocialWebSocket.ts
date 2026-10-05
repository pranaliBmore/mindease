import { useCallback, useEffect, useRef } from "react";
import type { MatchSession } from "@/lib/api";

export interface WsDirectMessagePayload {
  id: string;
  from_user_id: string;
  to_user_id: string;
  body: string;
  created_at: string;
}

export interface WsMatchMessagePayload {
  id: string;
  session_id: string;
  from_user_id: string;
  body: string;
  created_at: string;
}

function buildWsUrl(token: string): string {
  // In production VITE_API_BASE_URL points at the separately-hosted backend; derive the
  // socket origin from it. Locally it is empty and we use the Vite dev proxy (same origin).
  const apiBase = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.replace(/\/$/, "");
  const origin = apiBase
    ? apiBase.replace(/^http/, "ws")
    : `${window.location.protocol === "https:" ? "wss:" : "ws:"}//${window.location.host}`;
  return `${origin}/ws/social?token=${encodeURIComponent(token)}`;
}

export function useSocialWebSocket(
  token: string | null,
  handlers: {
    onDm?: (message: WsDirectMessagePayload) => void;
    onConnectionStateChanged?: () => void;
    onMatchFound?: (session: MatchSession) => void;
    onMatchMessage?: (message: WsMatchMessagePayload) => void;
    onMatchEnded?: (sessionId: string) => void;
    onMatchSafety?: (detail: string) => void;
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
          message?: WsDirectMessagePayload | WsMatchMessagePayload;
          session?: MatchSession;
          session_id?: string;
          detail?: string;
        };
        if (data.type === "dm" && data.message) {
          handlersRef.current.onDm?.(data.message as WsDirectMessagePayload);
        }
        if (data.type === "connection_state_changed") {
          handlersRef.current.onConnectionStateChanged?.();
        }
        if (data.type === "match_found" && data.session) {
          handlersRef.current.onMatchFound?.(data.session);
        }
        if (data.type === "match_message" && data.message) {
          handlersRef.current.onMatchMessage?.(data.message as WsMatchMessagePayload);
        }
        if (data.type === "match_ended" && typeof data.session_id === "string") {
          handlersRef.current.onMatchEnded?.(data.session_id);
        }
        if (data.type === "match_safety" && typeof data.detail === "string") {
          handlersRef.current.onMatchSafety?.(data.detail);
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

  const sendMatchMessage = useCallback((sessionId: string, text: string) => {
    const ws = wsRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN) {
      handlersRef.current.onWsError?.("Chat connection lost. Refresh the page.");
      return;
    }
    ws.send(JSON.stringify({ type: "match_message", session_id: sessionId, text }));
  }, []);

  return { sendDm, sendMatchMessage };
}
