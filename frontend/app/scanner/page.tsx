"use client";

import { useEffect, useState } from "react";
import { ArrowDown, Radio } from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { EmptyState, ErrorState, LoadingSkeleton, Spinner } from "@/components/EmptyState";
import { useLiveWebSocket } from "@/hooks/useLiveWebSocket";
import { apiFetch, cn } from "@/lib/utils";
import type { ScannerRow } from "@/lib/types";

interface ScannerStatus {
  state: string;
  backfill_done?: number;
  backfill_total?: number;
}

const statusStyles: Record<string, string> = {
  running: "bg-buy-soft text-buy",
  starting: "bg-warning-soft text-warning",
  stopped: "bg-surface-2 text-muted",
};

export default function ScannerPage() {
  const [rows, setRows] = useState<ScannerRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [sortKey, setSortKey] = useState<keyof ScannerRow>("buy_score");
  const [scannerStatus, setScannerStatus] = useState<ScannerStatus>({ state: "stopped" });
  const [actionError, setActionError] = useState("");
  const { connectionState, snapshot } = useLiveWebSocket((msg) => {
    if (msg.type === "scanner_status") {
      setScannerStatus(msg.data as ScannerStatus);
    }
    if (msg.type === "live_rows_update") {
      setRows(msg.data as ScannerRow[]);
      setLoading(false);
    }
  });

  useEffect(() => {
    if (snapshot?.live_rows) {
      setRows(snapshot.live_rows as ScannerRow[]);
      setLoading(false);
    }
    if (snapshot?.scanner) {
      setScannerStatus(snapshot.scanner as ScannerStatus);
    }
  }, [snapshot]);

  useEffect(() => {
    apiFetch<ScannerRow[]>("/api/v1/scanner/live")
      .then(setRows)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
    apiFetch<ScannerStatus>("/api/v1/scanner/status")
      .then(setScannerStatus)
      .catch(() => setScannerStatus({ state: "stopped" }));
  }, []);

  const sorted = [...rows].sort((a, b) => {
    const av = a[sortKey];
    const bv = b[sortKey];
    if (typeof av === "number" && typeof bv === "number") return bv - av;
    return String(av).localeCompare(String(bv));
  });

  const isStarting = scannerStatus.state === "starting";
  const isRunning = scannerStatus.state === "running";
  const progress =
    isStarting && scannerStatus.backfill_total
      ? `Loading candles ${scannerStatus.backfill_done ?? 0}/${scannerStatus.backfill_total}…`
      : "Starting scanner…";

  const startScanner = async () => {
    try {
      setActionError("");
      await apiFetch("/api/v1/scanner/start", { method: "POST" });
    } catch (e) {
      setActionError(e instanceof Error ? e.message : "Start failed — save Upstox Analytics Token in Settings first");
    }
  };

  const stopScanner = async () => {
    setActionError("");
    await apiFetch("/api/v1/scanner/stop", { method: "POST" });
  };

  return (
    <AppShell wsState={connectionState}>
      <div className="mb-4 flex flex-col gap-3 rounded-xl border border-border bg-surface p-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-3">
          <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-accent-soft text-accent">
            <Radio className="h-4 w-4" strokeWidth={2.25} />
          </span>
          <div>
            <p className="text-sm font-semibold text-foreground">Scanner</p>
            <span className={cn("inline-block rounded-full px-2 py-0.5 text-xs font-medium capitalize", statusStyles[scannerStatus.state] || statusStyles.stopped)}>
              {scannerStatus.state}
            </span>
          </div>
        </div>
        <div className="flex gap-2">
          <button
            onClick={startScanner}
            disabled={isStarting || isRunning}
            className="min-h-11 cursor-pointer rounded-lg bg-accent px-4 py-2.5 text-sm font-medium text-accent-foreground transition-colors hover:bg-accent-hover disabled:cursor-not-allowed disabled:opacity-50"
          >
            {isStarting ? "Starting…" : "Start Scanner"}
          </button>
          <button
            onClick={stopScanner}
            disabled={!isRunning && !isStarting}
            className="min-h-11 cursor-pointer rounded-lg border border-border px-4 py-2.5 text-sm font-medium text-foreground transition-colors hover:bg-surface-2 disabled:cursor-not-allowed disabled:opacity-50"
          >
            Stop Scanner
          </button>
        </div>
      </div>

      {actionError && <ErrorState message={actionError} />}
      {error && <ErrorState message={error} />}
      {isStarting && <Spinner label={progress} />}
      {loading && !isStarting && <LoadingSkeleton />}
      {!loading && !isStarting && sorted.length === 0 && (
        <EmptyState title="Scanner not running" description="Connect Upstox in Settings, then start the scanner above." />
      )}
      {sorted.length > 0 && (
        <div className="overflow-x-auto rounded-xl border border-border bg-surface">
          <table className="min-w-full text-sm">
            <thead className="border-b border-border bg-surface-2 text-left text-xs uppercase tracking-wide text-muted">
              <tr>
                {[
                  ["symbol", "Symbol"],
                  ["ltp", "LTP"],
                  ["change_pct", "Chg%"],
                  ["buy_score", "BUY"],
                  ["sell_score", "SELL"],
                  ["rvol", "RVOL"],
                  ["ema_trend", "EMA"],
                  ["vwap_state", "VWAP"],
                  ["htf", "HTF"],
                  ["source", "Source"],
                ].map(([key, label]) => (
                  <th
                    key={key}
                    className="cursor-pointer select-none whitespace-nowrap px-3 py-2.5 transition-colors hover:text-foreground"
                    onClick={() => setSortKey(key as keyof ScannerRow)}
                  >
                    <span className="inline-flex items-center gap-1">
                      {label}
                      {sortKey === key && <ArrowDown className="h-3 w-3 text-accent" strokeWidth={2.5} />}
                    </span>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {sorted.map((row) => (
                <tr key={row.instrument_key} className="border-b border-border transition-colors last:border-0 hover:bg-surface-2">
                  <td className="px-3 py-2.5 font-medium text-foreground">{row.symbol}</td>
                  <td className="px-3 py-2.5 font-mono-num">₹{row.ltp.toFixed(2)}</td>
                  <td
                    className={cn(
                      "px-3 py-2.5 font-mono-num font-medium",
                      row.change_pct > 0 ? "text-buy" : row.change_pct < 0 ? "text-sell" : "text-muted"
                    )}
                  >
                    {row.change_pct > 0 ? "+" : ""}
                    {row.change_pct.toFixed(2)}%
                  </td>
                  <td className="px-3 py-2.5 font-mono-num text-buy">{row.buy_score}</td>
                  <td className="px-3 py-2.5 font-mono-num text-sell">{row.sell_score}</td>
                  <td className="px-3 py-2.5 font-mono-num">{row.rvol.toFixed(2)}x</td>
                  <td className="px-3 py-2.5 text-muted">{row.ema_trend}</td>
                  <td className="px-3 py-2.5 text-muted">{row.vwap_state}</td>
                  <td className="px-3 py-2.5 text-muted">{row.htf}</td>
                  <td className="px-3 py-2.5 text-muted">{row.source}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </AppShell>
  );
}
