"use client";

import { useEffect, useState } from "react";
import { Lock, TrendingUp, User } from "lucide-react";
import { setToken } from "@/lib/auth";
import { API_URL, apiFetch } from "@/lib/utils";

export default function LoginPage() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [configured, setConfigured] = useState<boolean | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch(`${API_URL}/api/v1/auth/status`, {
          signal: AbortSignal.timeout(5000),
        });
        if (!res.ok) throw new Error("status failed");
        const data = (await res.json()) as { configured: boolean };
        if (!cancelled) setConfigured(Boolean(data.configured));
      } catch {
        if (!cancelled) setConfigured(true);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const isSetup = configured === false;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const path = isSetup ? "/api/v1/auth/setup" : "/api/v1/auth/login";
      const res = await apiFetch<{ token: string }>(path, {
        method: "POST",
        body: JSON.stringify({ username, password }),
      });
      setToken(res.token);
      window.location.href = "/";
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4">
      <div className="w-full max-w-sm rounded-xl border border-border bg-surface p-8">
        <div className="mb-6 flex flex-col items-center gap-3">
          <span className="flex h-12 w-12 items-center justify-center rounded-lg bg-accent-soft text-accent">
            <TrendingUp className="h-6 w-6" strokeWidth={2.25} />
          </span>
          <div className="text-center">
            <h1 className="text-lg font-semibold text-foreground">NSE Intraday Scanner</h1>
            <p className="text-xs text-muted">
              {configured === null
                ? "Loading…"
                : isSetup
                  ? "Create your admin account"
                  : "Sign in to continue"}
            </p>
          </div>
        </div>
        <form onSubmit={handleSubmit} className="space-y-4">
          <label className="block text-sm text-muted">
            Username
            <div className="relative mt-1">
              <User className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-2" strokeWidth={2} />
              <input
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                autoFocus
                required
                minLength={3}
                autoComplete="username"
                className="min-h-11 w-full rounded-lg border border-border bg-surface-2 py-2.5 pl-10 pr-3 text-sm text-foreground focus:border-accent"
              />
            </div>
          </label>
          <label className="block text-sm text-muted">
            Password
            <div className="relative mt-1">
              <Lock className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-2" strokeWidth={2} />
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                minLength={isSetup ? 6 : 1}
                autoComplete={isSetup ? "new-password" : "current-password"}
                className="min-h-11 w-full rounded-lg border border-border bg-surface-2 py-2.5 pl-10 pr-3 text-sm text-foreground focus:border-accent"
              />
            </div>
          </label>
          {isSetup && (
            <p className="text-xs text-muted">
              First-time setup: choose a username (min 3) and password (min 6). This creates the only admin login.
            </p>
          )}
          {error && <p className="text-xs text-sell">{error}</p>}
          <button
            type="submit"
            disabled={loading || configured === null}
            className="min-h-11 w-full cursor-pointer rounded-lg bg-accent px-4 py-2.5 text-sm font-medium text-accent-foreground transition-colors hover:bg-accent-hover disabled:cursor-not-allowed disabled:opacity-50"
          >
            {loading
              ? isSetup
                ? "Creating…"
                : "Signing in…"
              : isSetup
                ? "Create account"
                : "Sign In"}
          </button>
        </form>
      </div>
    </div>
  );
}
