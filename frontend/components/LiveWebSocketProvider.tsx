"use client";

import {
  createContext,
  useCallback,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { getToken } from "@/lib/auth";
import { API_URL, WS_URL } from "@/lib/utils";
import type { WsMessage } from "@/lib/types";

type ConnectionState = "live" | "reconnecting" | "offline";
type MessageHandler = (msg: WsMessage) => void;

interface LiveWebSocketContextValue {
  connectionState: ConnectionState;
  snapshot: Record<string, unknown> | null;
  subscribe: (handler: MessageHandler) => () => void;
}

export const LiveWebSocketContext = createContext<LiveWebSocketContextValue | null>(null);

const RECONNECT_MS = 5000;

async function backendReachable(): Promise<boolean> {
  try {
    const res = await fetch(`${API_URL}/health`, {
      signal: AbortSignal.timeout(4000),
    });
    return res.ok;
  } catch {
    return false;
  }
}

export function LiveWebSocketProvider({ children }: { children: ReactNode }) {
  const [connectionState, setConnectionState] = useState<ConnectionState>("offline");
  const [snapshot, setSnapshot] = useState<Record<string, unknown> | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const subscribersRef = useRef(new Set<MessageHandler>());
  const connectIdRef = useRef(0);
  const activeRef = useRef(true);

  const scheduleReconnect = useCallback((connect: () => void) => {
    if (reconnectRef.current) clearTimeout(reconnectRef.current);
    reconnectRef.current = setTimeout(connect, RECONNECT_MS);
  }, []);

  const connect = useCallback(() => {
    if (!activeRef.current) return;

    const existing = wsRef.current;
    if (
      existing &&
      (existing.readyState === WebSocket.OPEN ||
        existing.readyState === WebSocket.CONNECTING)
    ) {
      return;
    }

    const token = getToken();
    if (!token) {
      setConnectionState("offline");
      scheduleReconnect(connect);
      return;
    }

    setConnectionState("reconnecting");

    void (async () => {
      const ok = await backendReachable();
      if (!activeRef.current) return;

      if (!ok) {
        setConnectionState("offline");
        scheduleReconnect(connect);
        return;
      }

      const id = ++connectIdRef.current;
      const ws = new WebSocket(`${WS_URL}?token=${encodeURIComponent(token)}`);
      wsRef.current = ws;

      ws.onopen = () => {
        if (!activeRef.current || id !== connectIdRef.current) {
          ws.close();
          return;
        }
        setConnectionState("live");
      };

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data) as WsMessage;
          if (msg.type === "snapshot") {
            setSnapshot(msg.data as Record<string, unknown>);
          }
          subscribersRef.current.forEach((handler) => handler(msg));
        } catch {
          /* ignore */
        }
      };

      ws.onclose = () => {
        if (wsRef.current === ws) wsRef.current = null;
        if (!activeRef.current || id !== connectIdRef.current) return;
        setConnectionState("offline");
        scheduleReconnect(connect);
      };

      ws.onerror = () => {
        ws.onclose = null;
        ws.close();
      };
    })();
  }, [scheduleReconnect]);

  useEffect(() => {
    activeRef.current = true;
    connect();

    return () => {
      activeRef.current = false;
      connectIdRef.current += 1;
      if (reconnectRef.current) {
        clearTimeout(reconnectRef.current);
        reconnectRef.current = null;
      }
      const ws = wsRef.current;
      if (!ws) return;

      if (ws.readyState === WebSocket.OPEN) {
        wsRef.current = null;
        ws.onclose = null;
        ws.close();
        return;
      }

      if (ws.readyState === WebSocket.CONNECTING) {
        ws.onmessage = null;
        ws.onopen = () => ws.close();
        ws.onerror = () => ws.close();
        ws.onclose = () => {
          if (wsRef.current === ws) wsRef.current = null;
        };
      }
    };
  }, [connect]);

  const subscribe = useCallback((handler: MessageHandler) => {
    subscribersRef.current.add(handler);
    return () => subscribersRef.current.delete(handler);
  }, []);

  return (
    <LiveWebSocketContext.Provider value={{ connectionState, snapshot, subscribe }}>
      {children}
    </LiveWebSocketContext.Provider>
  );
}
