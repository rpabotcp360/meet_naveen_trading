"use client";

import { useEffect, useState } from "react";
import { AlertOctagon, Clock } from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { ErrorState } from "@/components/EmptyState";
import { useLiveWebSocket } from "@/hooks/useLiveWebSocket";
import { apiFetch, cn } from "@/lib/utils";
import type { SystemStatus } from "@/lib/types";

const GOOD = ["ok", "connected", "running", "live", "true", "healthy", "active"];
const WARN = ["starting", "reconnecting", "pending", "degraded", "not_configured"];
const BAD = ["error", "failed", "disconnected", "stopped", "false", "offline", "unauthenticated"];

const toneStyles = {
  good: "bg-buy-soft text-buy",
  warn: "bg-warning-soft text-warning",
  bad: "bg-sell-soft text-sell",
  neutral: "bg-surface-2 text-muted",
};

function tone(val: string): "good" | "warn" | "bad" | "neutral" {
  const v = String(val).toLowerCase();
  if (GOOD.some((g) => v.includes(g))) return "good";
  if (WARN.some((w) => v.includes(w))) return "warn";
  if (BAD.some((b) => v.includes(b))) return "bad";
  return "neutral";
}

export default function StatusPage() {
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [error, setError] = useState("");
  const { connectionState } = useLiveWebSocket();

  useEffect(() => {
    const load = () =>
      apiFetch<SystemStatus>("/api/v1/system/status")
        .then(setStatus)
        .catch((e) => setError(e.message));
    load();
    const interval = setInterval(load, 5000);
    return () => clearInterval(interval);
  }, []);

  return (
    <AppShell wsState={connectionState}>
      {error && <ErrorState message={error} />}
      {status && (
        <div className="space-y-4">
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {[
              ["Backend", status.backend],
              ["Upstox REST", status.upstox_rest],
              ["Upstox WebSocket", status.upstox_websocket],
              ["Telegram", status.telegram],
              ["Scanner", status.scanner_state],
            ].map(([label, val]) => (
              <div key={label} className="flex items-center justify-between rounded-xl border border-border bg-surface p-4">
                <p className="text-sm font-medium text-foreground">{label}</p>
                <span className={cn("rounded-full px-2.5 py-1 text-xs font-medium", toneStyles[tone(String(val))])}>
                  {String(val)}
                </span>
              </div>
            ))}
            <div className="flex items-center justify-between rounded-xl border border-border bg-surface p-4">
              <p className="text-sm font-medium text-foreground">Subscribed</p>
              <span className="font-mono-num text-sm text-foreground">{status.subscribed_instruments}</span>
            </div>
          </div>
          <div className="flex flex-col gap-2 rounded-xl border border-border bg-surface p-4 text-sm sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-center gap-2 text-muted">
              <Clock className="h-4 w-4" strokeWidth={2.25} />
              <span>
                Uptime: <span className="font-mono-num text-foreground">{Math.floor(status.uptime_seconds / 60)}</span> minutes
              </span>
            </div>
            {status.last_error && (
              <div className="flex items-center gap-2 text-sell">
                <AlertOctagon className="h-4 w-4 shrink-0" strokeWidth={2.25} />
                <span>Last error: {status.last_error}</span>
              </div>
            )}
          </div>
        </div>
      )}
    </AppShell>
  );
}
