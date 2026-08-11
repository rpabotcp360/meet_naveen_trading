import { Archive, Clock, LogIn, ShieldAlert, Target, TrendingDown, TrendingUp, Wallet } from "lucide-react";
import { AlertTypeBadge } from "./AlertTypeBadge";
import type { Signal } from "@/lib/types";
import { cn, parseUtcDate } from "@/lib/utils";

interface SignalCardProps {
  signal: Signal;
  highlight?: boolean;
  onArchive?: (id: number) => void;
}

function formatTriggerWindow(candleStartIso: string | undefined, candleCloseIso: string): string {
  const close = parseUtcDate(candleCloseIso);
  const date = close.toLocaleDateString("en-IN", {
    timeZone: "Asia/Kolkata",
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
  const closeTime = close.toLocaleTimeString("en-IN", {
    timeZone: "Asia/Kolkata",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
  if (!candleStartIso) return `${date}, ${closeTime} IST`;
  const startTime = parseUtcDate(candleStartIso).toLocaleTimeString("en-IN", {
    timeZone: "Asia/Kolkata",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
  return `${date}, ${startTime}–${closeTime} IST`;
}

function formatMoney(amount: number): string {
  const sign = amount > 0 ? "+" : amount < 0 ? "-" : "";
  return `${sign}₹${Math.abs(amount).toFixed(2)}`;
}

function formatPct(pct: number): string {
  return `${pct > 0 ? "+" : ""}${pct.toFixed(2)}%`;
}

export function SignalCard({ signal, highlight, onArchive }: SignalCardProps) {
  const isBuy = signal.direction === "BUY";
  const sign = isBuy ? 1 : -1;
  const score = isBuy ? signal.buy_score : signal.sell_score;
  const triggerWindow = formatTriggerWindow(signal.candle_timestamp_utc, signal.generated_at_utc);

  const quantity = signal.quantity ?? 0;
  const hasQuantity = quantity > 0;
  const invested = signal.capital_used ?? (hasQuantity ? quantity * signal.entry : undefined);

  // For a BUY, a rise is profit; for a SELL, a fall is profit — this `sign`
  // flip lets one formula answer both without duplicating the math.
  const pnl = (level: number) => {
    const pct = ((level - signal.entry) / signal.entry) * 100 * sign;
    const amount = hasQuantity ? (level - signal.entry) * quantity * sign : null;
    return { pct, amount };
  };

  const priceBoxes = [
    {
      key: "entry",
      label: "Entry",
      icon: LogIn,
      value: signal.entry,
      tone: "accent" as const,
      pnl: null,
    },
    { key: "t1", label: "T1", icon: Target, value: signal.target_1, tone: "buy" as const, pnl: pnl(signal.target_1) },
    { key: "t2", label: "T2", icon: Target, value: signal.target_2, tone: "buy" as const, pnl: pnl(signal.target_2) },
    { key: "t3", label: "T3", icon: Target, value: signal.target_3, tone: "buy" as const, pnl: pnl(signal.target_3) },
    {
      key: "stop",
      label: "Stop Loss",
      icon: ShieldAlert,
      value: signal.stop_loss,
      tone: "sell" as const,
      pnl: pnl(signal.stop_loss),
    },
  ];

  const toneClasses = {
    accent: { border: "border-accent/30", bg: "bg-accent-soft", text: "text-accent", sub: "text-accent/80" },
    buy: { border: "border-buy/30", bg: "bg-buy-soft", text: "text-buy", sub: "text-buy/80" },
    sell: { border: "border-sell/30", bg: "bg-sell-soft", text: "text-sell", sub: "text-sell/80" },
  };

  return (
    <article
      className={cn(
        "relative overflow-hidden rounded-xl border bg-surface p-3 transition-shadow duration-300 sm:p-4",
        highlight ? "border-accent shadow-[0_0_0_1px_var(--accent)] animate-signal-flash" : "border-border"
      )}
    >
      <span
        className={cn("absolute inset-y-0 left-0 w-1", isBuy ? "bg-buy" : "bg-sell")}
        aria-hidden="true"
      />
      <div className="flex items-start justify-between gap-2 pl-2">
        <div className="min-w-0">
          <h3 className="truncate text-base font-semibold text-foreground sm:text-lg">{signal.symbol}</h3>
          {signal.company_name && <p className="truncate text-xs text-muted">{signal.company_name}</p>}
          <div className="mt-1.5 flex flex-wrap items-center gap-2">
            <AlertTypeBadge isRealtime={signal.is_realtime} />
            <span className="inline-flex items-center gap-1 text-[11px] text-muted-2">
              <Clock className="h-3 w-3 shrink-0" strokeWidth={2.25} />
              <span className="truncate">{triggerWindow} · 5m candle</span>
            </span>
          </div>
        </div>
        <div className="flex shrink-0 items-center gap-1.5">
          <span
            className={cn(
              "flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-semibold",
              isBuy ? "bg-buy-soft text-buy" : "bg-sell-soft text-sell"
            )}
          >
            {isBuy ? <TrendingUp className="h-3.5 w-3.5" strokeWidth={2.5} /> : <TrendingDown className="h-3.5 w-3.5" strokeWidth={2.5} />}
            {signal.direction}
          </span>
          {onArchive && (
            <button
              onClick={() => onArchive(signal.id)}
              title="Archive notification"
              aria-label="Archive notification"
              className="flex h-11 w-11 shrink-0 cursor-pointer items-center justify-center rounded-full text-muted transition-colors hover:bg-surface-2 hover:text-foreground"
            >
              <Archive className="h-4 w-4" strokeWidth={2} />
            </button>
          )}
        </div>
      </div>

      {/* Entry, T1-T3 and Stop Loss — every price needed to place and bracket
          the order, matched in size and separated only by color + icon so
          each one is identifiable at a glance. Stop Loss is last, on purpose. */}
      <div className="mt-3 grid grid-cols-3 gap-2 pl-2 sm:grid-cols-5 sm:gap-2.5">
        {priceBoxes.map((box) => {
          const colors = toneClasses[box.tone];
          const Icon = box.icon;
          return (
            <div key={box.key} className={cn("rounded-lg border p-2.5", colors.border, colors.bg)}>
              <p className={cn("flex items-center gap-1 text-[10px] font-semibold uppercase tracking-wide sm:text-[11px]", colors.text)}>
                <Icon className="h-3 w-3 shrink-0" strokeWidth={2.5} />
                {box.label}
              </p>
              <p className={cn("font-mono-num text-base font-bold leading-tight sm:text-xl", colors.text)}>
                ₹{box.value.toFixed(2)}
              </p>
              {box.pnl && box.pnl.amount !== null && (
                <p className={cn("font-mono-num text-[10px] sm:text-[11px]", colors.sub)}>
                  {formatMoney(box.pnl.amount)} ({formatPct(box.pnl.pct)})
                </p>
              )}
            </div>
          );
        })}
      </div>

      {/* Order specifics — quantity and capital, secondary to the price levels above */}
      <div className="mt-2.5 flex flex-wrap items-center gap-x-4 gap-y-1 pl-2 text-xs text-muted">
        <span>
          Qty <span className="font-mono-num font-medium text-foreground">{hasQuantity ? quantity : "—"}</span> shares
        </span>
        <span className="flex items-center gap-1">
          <Wallet className="h-3 w-3 shrink-0" strokeWidth={2.25} />
          Invested{" "}
          <span className="font-mono-num font-medium text-foreground">
            {invested !== undefined ? `₹${invested.toFixed(0)}` : "—"}
          </span>
        </span>
        <span className="rounded-md bg-surface-2 px-2 py-1 text-muted">HTF {signal.htf_direction}</span>
        <span className="rounded-md bg-surface-2 px-2 py-1 text-muted">{signal.universe_source}</span>
      </div>

      {/* Supporting context — secondary to the trade decision */}
      <div className="mt-2.5 flex flex-wrap items-center gap-x-4 gap-y-1.5 pl-2 text-xs text-muted">
        <span className="flex items-center gap-1.5">
          Score
          <span className={cn("font-mono-num font-medium", isBuy ? "text-buy" : "text-sell")}>{score}</span>
          <span className="h-1.5 w-10 overflow-hidden rounded-full bg-surface-2">
            <span
              className={cn("block h-full rounded-full", isBuy ? "bg-buy" : "bg-sell")}
              style={{ width: `${Math.min(100, Math.max(0, score))}%` }}
            />
          </span>
        </span>
        <span>
          RVOL <span className="font-mono-num text-foreground">{signal.rvol.toFixed(2)}x</span>
        </span>
      </div>
    </article>
  );
}
