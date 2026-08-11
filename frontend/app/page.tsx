"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Activity, CalendarClock, Radio, TrendingDown, TrendingUp } from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { EmptyState, ErrorState, LoadingSkeleton, Spinner } from "@/components/EmptyState";
import { MetricCard } from "@/components/MetricCard";
import { SignalCard } from "@/components/SignalCard";
import { useLiveWebSocket } from "@/hooks/useLiveWebSocket";
import { apiFetch, cn } from "@/lib/utils";
import type { Signal, WsMessage } from "@/lib/types";

interface AutoModeStatus {
  enabled: boolean;
  next_start: string | null;
  next_stop: string | null;
}

function formatScheduleTime(iso: string): string {
  return new Date(iso).toLocaleString("en-IN", {
    timeZone: "Asia/Kolkata",
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
}

export default function DashboardPage() {
  const [signals, setSignals] = useState<Signal[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [highlightId, setHighlightId] = useState<number | null>(null);
  const [scanner, setScanner] = useState<Record<string, unknown>>({});
  const [stockFilter, setStockFilter] = useState("ALL");

  const onMessage = useCallback((msg: WsMessage) => {
    if (msg.type === "signal_created") {
      const s = msg.data as Signal;
      if (s.direction !== "BUY") return;
      setSignals((prev) => [s, ...prev.filter((x) => x.id !== s.id)]);
      setHighlightId(s.id);
      setTimeout(() => setHighlightId(null), 3000);
    }
    if (msg.type === "signal_archived") {
      const { id } = msg.data as { id: number; archived: boolean };
      setSignals((prev) => prev.filter((x) => x.id !== id));
    }
    if (msg.type === "signals_reset") {
      setSignals([]);
    }
    if (msg.type === "scanner_status") {
      setScanner(msg.data as Record<string, unknown>);
    }
  }, []);

  const { connectionState, snapshot } = useLiveWebSocket(onMessage);

  useEffect(() => {
    if (snapshot?.signals) {
      setSignals((snapshot.signals as Signal[]).filter((s) => s.direction === "BUY" && !s.archived));
      setScanner((snapshot.scanner as Record<string, unknown>) || {});
      setLoading(false);
    }
  }, [snapshot]);

  useEffect(() => {
    apiFetch<Signal[]>("/api/v1/signals/latest?limit=30")
      .then((data) => setSignals(data.filter((s) => s.direction === "BUY" && !s.archived)))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  const archiveSignal = useCallback((id: number) => {
    setSignals((prev) => prev.filter((s) => s.id !== id));
    apiFetch(`/api/v1/signals/${id}`, {
      method: "PATCH",
      body: JSON.stringify({ archived: true }),
    }).catch((e) => setError(e instanceof Error ? e.message : "Failed to archive signal"));
  }, []);

  const uniqueStocks = useMemo(
    () => Array.from(new Set(signals.map((s) => s.symbol))).sort(),
    [signals]
  );
  const visibleSignals = useMemo(
    () => (stockFilter === "ALL" ? signals : signals.filter((s) => s.symbol === stockFilter)),
    [signals, stockFilter]
  );

  const autoMode = scanner.auto_mode as AutoModeStatus | undefined;
  const isRunning = scanner.state === "running" || scanner.state === "starting";

  return (
    <AppShell wsState={connectionState}>
      <div className="mb-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <MetricCard label="Scanning" value={String(scanner.symbols_scanned ?? "—")} icon={Radio} tone="accent" />
        <MetricCard label="BUY Today" value={String(scanner.buy_signals_today ?? 0)} icon={TrendingUp} tone="buy" />
        <MetricCard label="SELL Today" value={String(scanner.sell_signals_today ?? 0)} icon={TrendingDown} tone="sell" />
        <MetricCard label="Scanner" value={String(scanner.state ?? "stopped")} icon={Activity} />
        {scanner.state === "starting" && (
          <div className="col-span-2 sm:col-span-4">
            <Spinner
              label={`Starting… ${scanner.backfill_done ?? 0}/${scanner.backfill_total ?? "—"} symbols`}
            />
          </div>
        )}
      </div>

      {autoMode && (
        <div className="mb-6 flex flex-wrap items-center gap-x-6 gap-y-2 rounded-xl border border-border bg-surface p-4 text-sm">
          <span className="flex items-center gap-1.5 font-medium text-foreground">
            <CalendarClock className="h-4 w-4 text-accent" strokeWidth={2.25} />
            Auto Mode:{" "}
            <span className={cn(autoMode.enabled ? "text-buy" : "text-muted")}>
              {autoMode.enabled ? "Enabled" : "Disabled"}
            </span>
          </span>
          {!isRunning && autoMode.next_start && (
            <span className="text-muted">
              Next auto-start:{" "}
              <span className="font-mono-num text-foreground">{formatScheduleTime(autoMode.next_start)}</span>
            </span>
          )}
          {isRunning && autoMode.next_stop && (
            <span className="text-muted">
              Next auto-stop:{" "}
              <span className="font-mono-num text-foreground">{formatScheduleTime(autoMode.next_stop)}</span>
            </span>
          )}
        </div>
      )}

      {uniqueStocks.length > 1 && (
        <div className="mb-4 flex items-center gap-2">
          <label htmlFor="stock-filter" className="text-sm text-muted">
            Filter by stock
          </label>
          <select
            id="stock-filter"
            value={stockFilter}
            onChange={(e) => setStockFilter(e.target.value)}
            className="min-h-11 rounded-lg border border-border bg-surface-2 px-3 py-2 text-sm text-foreground focus:border-accent"
          >
            <option value="ALL">All ({signals.length})</option>
            {uniqueStocks.map((sym) => (
              <option key={sym} value={sym}>
                {sym} ({signals.filter((s) => s.symbol === sym).length})
              </option>
            ))}
          </select>
        </div>
      )}

      {error && <ErrorState message={error} />}
      {loading && <LoadingSkeleton />}
      {!loading && visibleSignals.length === 0 && (
        <EmptyState title="No active BUY signals" description="BUY signals appear here when conditions are met on completed 5m candles." />
      )}
      <div className="space-y-3">
        {visibleSignals.map((s) => (
          <SignalCard
            key={s.id ?? `${s.symbol}-${s.generated_at_utc}`}
            signal={s}
            highlight={highlightId === s.id}
            onArchive={archiveSignal}
          />
        ))}
      </div>
    </AppShell>
  );
}
