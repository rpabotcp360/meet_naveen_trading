"use client";

import { useCallback, useEffect, useState } from "react";
import { Archive, ArchiveRestore, Check, CheckCircle2, Circle, Minus, XCircle } from "lucide-react";
import { AlertTypeBadge } from "@/components/AlertTypeBadge";
import { AppShell } from "@/components/AppShell";
import { EmptyState, ErrorState, LoadingSkeleton } from "@/components/EmptyState";
import { useLiveWebSocket } from "@/hooks/useLiveWebSocket";
import { apiFetch, cn, parseUtcDate } from "@/lib/utils";
import type { Signal, WsMessage } from "@/lib/types";

type FilterKey = "" | "BUY" | "SELL" | "ACHIEVED";

const FILTERS: { key: FilterKey; label: string }[] = [
  { key: "", label: "All" },
  { key: "BUY", label: "BUY" },
  { key: "SELL", label: "SELL" },
  { key: "ACHIEVED", label: "Achieved" },
];

function OutcomeBadge({ outcome }: { outcome?: string }) {
  if (outcome === "achieved") {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-buy-soft px-2 py-0.5 text-xs font-semibold text-buy">
        <CheckCircle2 className="h-3.5 w-3.5" strokeWidth={2.5} />
        Achieved
      </span>
    );
  }
  if (outcome === "stopped") {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-sell-soft px-2 py-0.5 text-xs font-semibold text-sell">
        <XCircle className="h-3.5 w-3.5" strokeWidth={2.5} />
        Stopped
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 rounded-full bg-surface-2 px-2 py-0.5 text-xs font-medium text-muted">
      <Circle className="h-3.5 w-3.5" strokeWidth={2.5} />
      Open
    </span>
  );
}

export default function HistoryPage() {
  const [signals, setSignals] = useState<Signal[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [filter, setFilter] = useState<FilterKey>("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");

  const onMessage = useCallback((msg: WsMessage) => {
    if (msg.type === "signals_reset") {
      setSignals([]);
    }
  }, []);
  const { connectionState } = useLiveWebSocket(onMessage);

  useEffect(() => {
    const params = new URLSearchParams({ limit: "100" });
    if (filter === "BUY" || filter === "SELL") params.set("direction", filter);
    if (filter === "ACHIEVED") params.set("outcome", "achieved");
    if (dateFrom) params.set("date_from", dateFrom);
    if (dateTo) params.set("date_to", dateTo);
    setLoading(true);
    apiFetch<Signal[]>(`/api/v1/signals?${params.toString()}`)
      .then(setSignals)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [filter, dateFrom, dateTo]);

  const toggleArchive = (signal: Signal) => {
    const archived = !signal.archived;
    setSignals((prev) => prev.map((s) => (s.id === signal.id ? { ...s, archived } : s)));
    apiFetch(`/api/v1/signals/${signal.id}`, {
      method: "PATCH",
      body: JSON.stringify({ archived }),
    }).catch((e) => {
      setSignals((prev) => prev.map((s) => (s.id === signal.id ? { ...s, archived: !archived } : s)));
      setError(e instanceof Error ? e.message : "Failed to update signal");
    });
  };

  return (
    <AppShell wsState={connectionState}>
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <div className="inline-flex gap-1 rounded-lg border border-border bg-surface p-1">
          {FILTERS.map((f) => (
            <button
              key={f.key || "all"}
              onClick={() => setFilter(f.key)}
              className={cn(
                "min-h-11 cursor-pointer rounded-md px-3 py-2 text-sm font-medium transition-colors duration-150",
                filter === f.key ? "bg-accent text-accent-foreground" : "text-muted hover:text-foreground"
              )}
            >
              {f.label}
            </button>
          ))}
        </div>

        <div className="flex flex-wrap items-center gap-2 text-sm text-muted">
          <label htmlFor="date-from">From</label>
          <input
            id="date-from"
            type="date"
            value={dateFrom}
            max={dateTo || undefined}
            onChange={(e) => setDateFrom(e.target.value)}
            className="min-h-11 min-w-0 rounded-lg border border-border bg-surface-2 px-3 py-2 text-sm text-foreground focus:border-accent"
          />
          <label htmlFor="date-to">To</label>
          <input
            id="date-to"
            type="date"
            value={dateTo}
            min={dateFrom || undefined}
            onChange={(e) => setDateTo(e.target.value)}
            className="min-h-11 min-w-0 rounded-lg border border-border bg-surface-2 px-3 py-2 text-sm text-foreground focus:border-accent"
          />
          {(dateFrom || dateTo) && (
            <button
              onClick={() => {
                setDateFrom("");
                setDateTo("");
              }}
              className="min-h-11 cursor-pointer rounded-lg px-2 text-sm text-muted underline-offset-2 hover:text-foreground hover:underline"
            >
              Clear
            </button>
          )}
        </div>
      </div>

      {error && <ErrorState message={error} />}
      {loading && <LoadingSkeleton />}
      {!loading && signals.length === 0 && <EmptyState title="No signal history" />}
      {!loading && signals.length > 0 && (
        <div className="overflow-x-auto rounded-xl border border-border bg-surface">
          <table className="min-w-full text-sm">
            <thead className="border-b border-border bg-surface-2 text-left text-xs uppercase tracking-wide text-muted">
              <tr>
                <th className="px-3 py-2.5">Time</th>
                <th className="px-3 py-2.5">Alert</th>
                <th className="px-3 py-2.5">Symbol</th>
                <th className="px-3 py-2.5">Dir</th>
                <th className="px-3 py-2.5">Entry</th>
                <th className="px-3 py-2.5">SL</th>
                <th className="px-3 py-2.5">Score</th>
                <th className="px-3 py-2.5">Outcome</th>
                <th className="px-3 py-2.5">Source</th>
                <th className="px-3 py-2.5">Telegram</th>
                <th className="px-3 py-2.5">Notification</th>
              </tr>
            </thead>
            <tbody>
              {signals.map((s) => (
                <tr key={s.id} className="border-b border-border transition-colors last:border-0 hover:bg-surface-2">
                  <td className="whitespace-nowrap px-3 py-2.5 font-mono-num text-muted">
                    {parseUtcDate(s.generated_at_utc).toLocaleString("en-IN", { timeZone: "Asia/Kolkata" })}
                  </td>
                  <td className="px-3 py-2.5">
                    <AlertTypeBadge isRealtime={s.is_realtime} />
                  </td>
                  <td className="px-3 py-2.5 font-medium text-foreground">{s.symbol}</td>
                  <td className="px-3 py-2.5">
                    <span
                      className={cn(
                        "rounded-full px-2 py-0.5 text-xs font-semibold",
                        s.direction === "BUY" ? "bg-buy-soft text-buy" : "bg-sell-soft text-sell"
                      )}
                    >
                      {s.direction}
                    </span>
                  </td>
                  <td className="px-3 py-2.5 font-mono-num">₹{s.entry.toFixed(2)}</td>
                  <td className="px-3 py-2.5 font-mono-num text-sell">₹{s.stop_loss.toFixed(2)}</td>
                  <td className="px-3 py-2.5 font-mono-num">{s.direction === "BUY" ? s.buy_score : s.sell_score}</td>
                  <td className="px-3 py-2.5">
                    <OutcomeBadge outcome={s.outcome} />
                  </td>
                  <td className="px-3 py-2.5 text-muted">{s.universe_source}</td>
                  <td className="px-3 py-2.5">
                    {s.telegram_sent ? (
                      <Check className="h-4 w-4 text-buy" strokeWidth={2.5} />
                    ) : (
                      <Minus className="h-4 w-4 text-muted-2" strokeWidth={2.5} />
                    )}
                  </td>
                  <td className="px-3 py-2.5">
                    <button
                      onClick={() => toggleArchive(s)}
                      title={s.archived ? "Unarchive — show on Dashboard again" : "Archive this notification"}
                      className={cn(
                        "flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-xs font-medium transition-colors cursor-pointer",
                        s.archived ? "bg-surface-2 text-muted" : "bg-accent-soft text-accent"
                      )}
                    >
                      {s.archived ? (
                        <ArchiveRestore className="h-3.5 w-3.5" strokeWidth={2.25} />
                      ) : (
                        <Archive className="h-3.5 w-3.5" strokeWidth={2.25} />
                      )}
                      {s.archived ? "Archived" : "Active"}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </AppShell>
  );
}
