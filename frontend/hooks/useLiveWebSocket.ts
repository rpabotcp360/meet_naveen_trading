"use client";

import { useContext, useEffect, useRef } from "react";
import { LiveWebSocketContext } from "@/components/LiveWebSocketProvider";
import type { WsMessage } from "@/lib/types";

export function useLiveWebSocket(onMessage?: (msg: WsMessage) => void) {
  const ctx = useContext(LiveWebSocketContext);
  if (!ctx) {
    throw new Error("useLiveWebSocket must be used within LiveWebSocketProvider");
  }

  const onMessageRef = useRef(onMessage);
  onMessageRef.current = onMessage;

  useEffect(() => {
    if (!onMessageRef.current) return;
    return ctx.subscribe((msg) => onMessageRef.current?.(msg));
  }, [ctx.subscribe]);

  return { connectionState: ctx.connectionState, snapshot: ctx.snapshot };
}
