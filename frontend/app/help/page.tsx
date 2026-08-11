"use client";

import type { LucideIcon } from "lucide-react";
import {
  Activity,
  AlarmClock,
  BarChart3,
  Bell,
  CalendarClock,
  CheckCircle2,
  Filter,
  Gauge,
  ShieldAlert,
  Target,
  TrendingUp,
} from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { useLiveWebSocket } from "@/hooks/useLiveWebSocket";

function Step({
  n,
  icon: Icon,
  title,
  children,
}: {
  n: number;
  icon: LucideIcon;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex gap-4 rounded-xl border border-border bg-surface p-5">
      <div className="flex flex-col items-center">
        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-accent-soft font-mono-num text-sm font-bold text-accent">
          {n}
        </span>
        <span className="mt-2 h-full w-px bg-border" />
      </div>
      <div className="min-w-0 flex-1 pb-2">
        <h3 className="mb-2 flex items-center gap-2 text-base font-semibold text-foreground">
          <Icon className="h-4 w-4 shrink-0 text-accent" strokeWidth={2.25} />
          {title}
        </h3>
        <div className="space-y-3 text-sm leading-relaxed text-muted">{children}</div>
      </div>
    </div>
  );
}

function Tech({ children }: { children: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-border-strong bg-surface-2 p-3">
      <p className="mb-1 text-[11px] font-semibold uppercase tracking-wide text-accent">Technical</p>
      <div className="font-mono-num text-[13px] leading-relaxed text-foreground">{children}</div>
    </div>
  );
}

function Plain({ children }: { children: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-border bg-surface p-3">
      <p className="mb-1 text-[11px] font-semibold uppercase tracking-wide text-buy">In plain English</p>
      <p className="text-[13px] leading-relaxed text-foreground">{children}</p>
    </div>
  );
}

export default function HelpPage() {
  const { connectionState } = useLiveWebSocket();

  return (
    <AppShell wsState={connectionState}>
      <div className="mx-auto max-w-3xl">
        <div className="mb-6">
          <h1 className="text-xl font-semibold text-foreground">How a notification gets triggered</h1>
          <p className="mt-1 text-sm text-muted">
            Everything below describes exactly what this app does, step by step — no marketing language, this is
            the real logic (ported from the "Naveen Intraday Long Only V3.2" Pine Script strategy).
          </p>
        </div>

        <div className="space-y-4">
          <Step n={1} icon={BarChart3} title="Every stock's price is rebuilt into 5-minute candles">
            <Tech>
              A live tick stream from Upstox is aggregated into 5-minute OHLCV candles per symbol. A signal is
              only ever evaluated once a candle <em>closes</em> — never on a still-forming candle.
            </Tech>
            <Plain>
              Think of it like a stopwatch that resets every 5 minutes. The app waits for that 5-minute window to
              fully finish before it even looks at whether to buy — it never reacts to a mid-candle wiggle.
            </Plain>
          </Step>

          <Step n={2} icon={Activity} title="Ten indicators are computed on the closed candle">
            <Tech>
              EMA 9 / EMA 21 / EMA 200, VWAP (resets every session), RSI 14, MACD 12/26/9, Supertrend (factor
              depends on mode, ATR length 10), ATR 14, 20-period average volume, 20-candle breakout high/low, and
              a 15-minute higher-timeframe EMA 50 bias.
            </Tech>
            <Plain>
              These are the standard tools traders use to answer: "is this stock trending up, is it above its
              average price today, is momentum strong, is volume unusually high, and does the bigger 15-minute
              picture agree?"
            </Plain>
          </Step>

          <Step n={3} icon={Gauge} title="Those ten signals are combined into a BUY Score out of 100">
            <Tech>
              EMA bullish +15, price above VWAP +15, Supertrend bullish +15, RSI &gt; 50 +10, MACD bullish +10,
              volume above average +10, volume spike (&gt;1.3× average) +5, price breaks above the prior 20-candle
              high +10, 15m trend bullish +5, price above EMA 200 +5. A mirrored Sell Score is computed the same
              way for the bearish version of each condition.
            </Tech>
            <Plain>
              Nothing fires off a single indicator. The app checks ten things and adds up points for however many
              agree — the more of them that line up bullish at once, the higher the score.
            </Plain>
          </Step>

          <Step n={4} icon={Filter} title="A candle only qualifies as a 'setup' if every one of these is true">
            <Tech>
              <ul className="list-disc space-y-1 pl-5">
                <li>Inside the entry window, 09:30–14:45 IST (opening range 09:15–09:30 is excluded)</li>
                <li>BUY Score ≥ threshold (65 in Balanced mode; 58 Aggressive; 78 Conservative)</li>
                <li>BUY Score is strictly higher than the Sell Score</li>
                <li>EMA 9 &gt; EMA 21 (short-term uptrend) and price is above VWAP</li>
                <li>Price has closed above the 09:15–09:30 opening-range high</li>
                <li>
                  Price isn&apos;t too extended from VWAP: within 2× ATR normally, or 3× ATR if it&apos;s a genuine
                  breakout (above the 20-candle high <em>and</em> a volume spike)
                </li>
              </ul>
            </Tech>
            <Plain>
              This is the filter that says "don&apos;t chase." A stock can have a great score, but if it already
              ran too far from its average price today without real volume behind it, the app treats that as
              too risky to enter and skips it.
            </Plain>
          </Step>

          <Step n={5} icon={TrendingUp} title="A notification only fires on the transition into a setup — not every candle">
            <Tech>
              The app tracks a FLAT/LONG state per stock. A BUY alert fires only when: the setup condition just
              became true this candle (it was false the candle before), the stock is currently flat (no open
              position), and at least 3 candles (15 minutes) have passed since the last trade closed.
            </Tech>
            <Plain>
              Without this rule, a stock that stays in a great setup for an hour would spam you with a new alert
              every 5 minutes. Instead you get exactly one alert per genuine new opportunity, with a cooldown so
              it doesn&apos;t immediately re-fire right after a trade ends.
            </Plain>
          </Step>

          <Step n={6} icon={Target} title="Entry, Stop Loss and three Targets are calculated from ATR">
            <Tech>
              Entry = candle close. Stop Loss = Entry − 1.5×ATR. Target 1 = Entry + 1.5×ATR. Target 2 = Entry +
              3×ATR. Target 3 (shown for reference, not part of exit management) = Entry + 6×ATR. Position size =
              your configured capital per trade ÷ entry price, rounded down to whole shares.
            </Tech>
            <Plain>
              ATR measures how much a stock typically moves in a candle. The stop and targets scale with that —
              a jumpy stock gets a wider stop and wider targets than a calm one, instead of a fixed rupee amount
              for every stock.
            </Plain>
          </Step>

          <Step n={7} icon={ShieldAlert} title="Once in a trade, it's actively managed until it closes">
            <Tech>
              Half the position exits at Target 1, the other half at Target 2. The stop trails up to breakeven
              once price is 1× ATR in profit, and continues trailing at 1.5× ATR below the close every candle
              after that. If a strong bearish reversal appears (Sell Score ≥ Buy threshold, dominant, EMA and
              VWAP both bearish), the whole position exits immediately regardless of price.
            </Tech>
            <Plain>
              This is the same discipline a careful trader would apply by hand: lock in some profit early, move
              your stop to break-even so the trade can&apos;t turn into a loss once it&apos;s working, and get out
              fast if the trend clearly flips against you.
            </Plain>
          </Step>

          <Step n={8} icon={CheckCircle2} title="Every closed trade is tagged Achieved or Stopped">
            <Tech>
              "Achieved" means at least one target was hit before the position fully closed. "Stopped" means it
              closed via the stop-loss or the bearish emergency exit without ever reaching a target. This is what
              the History page&apos;s "Achieved" filter and the Outcome column show.
            </Tech>
            <Plain>
              A simple win/loss record for every alert, so you can look back and see how often the signals
              actually worked out.
            </Plain>
          </Step>

          <Step n={9} icon={Bell} title="The alert is sent to the Dashboard and Telegram">
            <Tech>
              A "Realtime Alert" is one detected live, tick by tick. A "Past Alert" is one found by replaying
              today&apos;s candles when the scanner is started or restarted mid-session, so a late start never
              silently misses a signal. Both are sent to Telegram as an image card with entry/targets/stop and
              % P&amp;L; both appear on the Dashboard, tagged accordingly.
            </Tech>
            <Plain>
              If you start the app at 1pm, it doesn&apos;t just start watching from 1pm onward — it first checks
              what already happened since market open and tells you about anything you would have otherwise
              missed.
            </Plain>
          </Step>

          <Step n={10} icon={CalendarClock} title="The scanner runs itself on a schedule">
            <Tech>
              Auto-start at 09:00 IST and auto-stop at 15:45 IST, Monday–Friday only. Before starting, it checks
              Upstox&apos;s market-status feed for a fresh update from today; if none appears (a likely holiday),
              it skips the day. As a second safety net, if no market data has arrived by 09:25 despite starting,
              it stops itself and tries again the next weekday.
            </Tech>
            <Plain>
              You don&apos;t have to remember to start it every morning or stop it every evening, and it&apos;s
              built to avoid sitting there uselessly "running" on a day the exchange is actually closed.
            </Plain>
          </Step>
        </div>

        <div className="mt-6 flex items-start gap-3 rounded-xl border border-border bg-surface p-4 text-sm text-muted">
          <AlarmClock className="mt-0.5 h-4 w-4 shrink-0 text-accent" strokeWidth={2.25} />
          <p>
            Strategy Mode (Settings → Trading) only changes the thresholds and Supertrend sensitivity —
            Aggressive is more permissive (score ≥ 58), Conservative is stricter (score ≥ 78). Everything else on
            this page stays the same across all three modes.
          </p>
        </div>
      </div>
    </AppShell>
  );
}
