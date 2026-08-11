"use client";

import { useEffect, useState } from "react";
import { AlertTriangle, CheckCircle2, KeyRound, Layers, Send, Wallet } from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { ConnectionBadge } from "@/components/ConnectionBadge";
import { ErrorState } from "@/components/EmptyState";
import { useLiveWebSocket } from "@/hooks/useLiveWebSocket";
import { apiFetch } from "@/lib/utils";

interface UpstoxStatus {
  configured: boolean;
  authenticated: boolean;
  auth_mode: string;
  last_auth_at: string;
}

const inputClass =
  "mt-1 min-h-11 w-full rounded-lg border border-border bg-surface-2 px-3 py-2.5 text-sm text-foreground placeholder:text-muted-2 focus:border-accent";
const primaryBtn =
  "min-h-11 cursor-pointer rounded-lg bg-accent px-4 py-2.5 text-sm font-medium text-accent-foreground transition-colors hover:bg-accent-hover disabled:cursor-not-allowed disabled:opacity-50";
const secondaryBtn =
  "min-h-11 cursor-pointer rounded-lg border border-border px-4 py-2.5 text-sm font-medium text-foreground transition-colors hover:bg-surface-2";
const destructiveBtn =
  "min-h-11 cursor-pointer rounded-lg border border-sell/30 px-4 py-2.5 text-sm font-medium text-sell transition-colors hover:bg-sell-soft disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:bg-transparent";

function SectionCard({
  icon: Icon,
  title,
  children,
}: {
  icon: React.ComponentType<{ className?: string; strokeWidth?: number }>;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section className="mb-6 rounded-xl border border-border bg-surface p-4 sm:p-5">
      <h2 className="mb-4 flex items-center gap-2 font-semibold text-foreground">
        <span className="flex h-7 w-7 items-center justify-center rounded-md bg-accent-soft text-accent">
          <Icon className="h-4 w-4" strokeWidth={2.25} />
        </span>
        {title}
      </h2>
      {children}
    </section>
  );
}

export default function SettingsPage() {
  const [settings, setSettings] = useState<Record<string, unknown>>({});
  const [upstoxStatus, setUpstoxStatus] = useState<UpstoxStatus | null>(null);
  const [telegramToken, setTelegramToken] = useState("");
  const [telegramChatId, setTelegramChatId] = useState("");
  const [upstoxToken, setUpstoxToken] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [showResetConfirm, setShowResetConfirm] = useState(false);
  const [resetConfirmText, setResetConfirmText] = useState("");
  const [resetting, setResetting] = useState(false);

  const { connectionState } = useLiveWebSocket();

  const loadUpstoxStatus = () =>
    apiFetch<UpstoxStatus>("/api/v1/upstox/status")
      .then(setUpstoxStatus)
      .catch(() => setUpstoxStatus(null));

  useEffect(() => {
    apiFetch<Record<string, unknown>>("/api/v1/settings")
      .then((s) => {
        setSettings(s);
        setTelegramChatId(String(s.telegram_chat_id || ""));
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load settings"));
    loadUpstoxStatus();
  }, []);

  const saveSettings = async (updates: Record<string, unknown>) => {
    try {
      const updated = await apiFetch<Record<string, unknown>>("/api/v1/settings", {
        method: "PATCH",
        body: JSON.stringify(updates),
      });
      setSettings(updated);
      setMessage("Settings saved");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Save failed");
    }
  };

  const saveTelegram = async () => {
    await apiFetch("/api/v1/telegram/config", {
      method: "POST",
      body: JSON.stringify({
        bot_token: telegramToken || undefined,
        chat_id: telegramChatId,
        enabled: true,
      }),
    });
    setTelegramToken("");
    setMessage("Telegram configured");
  };

  const testTelegram = async () => {
    const res = await apiFetch<{ ok: boolean; error?: string }>("/api/v1/telegram/test", { method: "POST" });
    setMessage(res.ok ? "Test notification sent" : res.error || "Failed");
  };

  const saveUpstoxToken = async () => {
    if (!upstoxToken.trim()) {
      setError("Paste your Upstox Analytics Token");
      return;
    }
    try {
      await apiFetch("/api/v1/upstox/config", {
        method: "POST",
        body: JSON.stringify({ access_token: upstoxToken.trim() }),
      });
      setUpstoxToken("");
      setError("");
      setMessage("Upstox Analytics Token saved");
      await loadUpstoxStatus();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Save failed");
    }
  };

  const disconnectUpstox = async () => {
    await apiFetch("/api/v1/upstox/disconnect", { method: "POST" });
    setMessage("Upstox disconnected");
    await loadUpstoxStatus();
  };

  const resetAllData = async () => {
    setResetting(true);
    try {
      await apiFetch("/api/v1/signals/reset", { method: "POST" });
      setMessage("All signal data has been reset — History and Dashboard are now empty");
      setShowResetConfirm(false);
      setResetConfirmText("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Reset failed");
    } finally {
      setResetting(false);
    }
  };

  return (
    <AppShell wsState={connectionState}>
      {error && <ErrorState message={error} />}
      {message && (
        <p className="mb-4 flex items-center gap-2 rounded-lg bg-buy-soft px-3 py-2 text-sm text-buy">
          <CheckCircle2 className="h-4 w-4 shrink-0" strokeWidth={2.25} />
          {message}
        </p>
      )}

      <SectionCard icon={Wallet} title="Trading">
        <div className="grid gap-3 sm:grid-cols-2">
          <label className="text-sm text-muted">
            Capital per trade (₹)
            <input
              type="number"
              defaultValue={Number(settings.capital_per_trade || 20000)}
              onBlur={(e) => saveSettings({ capital_per_trade: Number(e.target.value) })}
              className={`${inputClass} font-mono-num`}
            />
          </label>
          <label className="text-sm text-muted">
            Strategy mode
            <select
              defaultValue={String(settings.strategy_mode || "balanced")}
              onChange={(e) => saveSettings({ strategy_mode: e.target.value })}
              className={inputClass}
            >
              <option value="aggressive">Aggressive</option>
              <option value="balanced">Balanced</option>
              <option value="conservative">Conservative</option>
            </select>
          </label>
        </div>
      </SectionCard>

      <SectionCard icon={Layers} title="Scanning Universe">
        <p className="mb-3 text-sm text-muted">
          Choose which instruments the scanner monitors and generates signals for.
        </p>
        <label className="text-sm text-muted">
          Universe source
          <select
            defaultValue={String(settings.universe_source || "BOTH")}
            onChange={(e) => saveSettings({ universe_source: e.target.value })}
            className={inputClass}
          >
            <option value="TOP30">Top 30 (rank-based)</option>
            <option value="WATCHLIST">Watch List only</option>
            <option value="BOTH">Top 30 + Watch List (both)</option>
          </select>
        </label>
      </SectionCard>

      <SectionCard icon={KeyRound} title="Upstox Analytics Token">
        <p className="mb-3 text-sm text-muted">
          Upstox Analytics provides a long-lived read-only token (no Client Secret needed). Copy it from
          Upstox Developer Console → Analytics tab.
        </p>
        {upstoxStatus && (
          <div className="mb-3">
            <ConnectionBadge
              label="Upstox"
              state={upstoxStatus.authenticated ? "connected" : "disconnected"}
            />
          </div>
        )}
        <div className="grid gap-3">
          <textarea
            placeholder="Paste Analytics Token (eyJ...)"
            value={upstoxToken}
            onChange={(e) => setUpstoxToken(e.target.value)}
            rows={3}
            className={`${inputClass} mt-0 font-mono-num text-xs`}
          />
          <div className="flex gap-2">
            <button onClick={saveUpstoxToken} className={primaryBtn}>
              Save Token
            </button>
            {upstoxStatus?.authenticated && (
              <button onClick={disconnectUpstox} className={destructiveBtn}>
                Disconnect
              </button>
            )}
          </div>
        </div>
      </SectionCard>

      <SectionCard icon={Send} title="Telegram">
        <details className="mb-3 text-sm text-muted">
          <summary className="cursor-pointer font-medium text-foreground">Setup instructions</summary>
          <ol className="mt-2 list-decimal space-y-1 pl-5">
            <li>Open Telegram and search @BotFather</li>
            <li>Run /newbot and create a bot</li>
            <li>Copy the Bot Token</li>
            <li>Message your bot, then get Chat ID via getUpdates API</li>
            <li>Paste credentials below and send test notification</li>
          </ol>
        </details>
        <div className="grid gap-3">
          <input
            placeholder="Bot Token"
            type="password"
            value={telegramToken}
            onChange={(e) => setTelegramToken(e.target.value)}
            className={`${inputClass} mt-0`}
          />
          <input
            placeholder="Chat ID"
            value={telegramChatId}
            onChange={(e) => setTelegramChatId(e.target.value)}
            className={`${inputClass} mt-0`}
          />
          <div className="flex gap-2">
            <button onClick={saveTelegram} className={secondaryBtn}>
              Save
            </button>
            <button onClick={testTelegram} className={primaryBtn}>
              Send Test
            </button>
          </div>
        </div>
      </SectionCard>

      <SectionCard icon={AlertTriangle} title="Danger Zone">
        <p className="mb-3 text-sm text-muted">
          Permanently delete every signal — clears all cards from the Dashboard and every row in History.
          This cannot be undone.
        </p>
        <button onClick={() => setShowResetConfirm(true)} className={destructiveBtn}>
          Reset All Data
        </button>
      </SectionCard>

      {showResetConfirm && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 px-4 backdrop-blur-sm"
          onClick={() => !resetting && setShowResetConfirm(false)}
        >
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby="reset-dialog-title"
            onClick={(e) => e.stopPropagation()}
            className="w-full max-w-sm rounded-xl border border-sell/30 bg-surface p-5 shadow-xl"
          >
            <div className="mb-3 flex items-center gap-2.5">
              <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-sell-soft text-sell">
                <AlertTriangle className="h-4.5 w-4.5" strokeWidth={2.25} />
              </span>
              <h2 id="reset-dialog-title" className="text-base font-semibold text-foreground">
                Reset all signal data?
              </h2>
            </div>
            <p className="mb-4 text-sm leading-relaxed text-muted">
              This permanently deletes every signal from History and clears every notification card on the
              Dashboard. It does not affect your Watchlist or Settings. This cannot be undone.
            </p>
            <label className="mb-4 block text-sm text-muted">
              Type <span className="font-mono-num font-semibold text-foreground">RESET</span> to confirm
              <input
                autoFocus
                value={resetConfirmText}
                onChange={(e) => setResetConfirmText(e.target.value)}
                onKeyDown={(e) => e.key === "Escape" && setShowResetConfirm(false)}
                className={`${inputClass} font-mono-num`}
              />
            </label>
            <div className="flex justify-end gap-2">
              <button
                onClick={() => {
                  setShowResetConfirm(false);
                  setResetConfirmText("");
                }}
                disabled={resetting}
                className={secondaryBtn}
              >
                Cancel
              </button>
              <button
                onClick={resetAllData}
                disabled={resetConfirmText !== "RESET" || resetting}
                className={destructiveBtn}
              >
                {resetting ? "Resetting…" : "Delete Everything"}
              </button>
            </div>
          </div>
        </div>
      )}
    </AppShell>
  );
}
