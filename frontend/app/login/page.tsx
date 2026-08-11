"use client";

import { useState } from "react";
import { Lock, TrendingUp, User } from "lucide-react";
import { setToken } from "@/lib/auth";
import { apiFetch } from "@/lib/utils";

export default function LoginPage() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const res = await apiFetch<{ token: string }>("/api/v1/auth/login", {
        method: "POST",
        body: JSON.stringify({ username, password }),
      });
      setToken(res.token);
      // Hard navigation so every provider (WebSocket included) remounts
      // and immediately picks up the freshly stored token.
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
            <p className="text-xs text-muted">Sign in to continue</p>
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
                autoComplete="current-password"
                className="min-h-11 w-full rounded-lg border border-border bg-surface-2 py-2.5 pl-10 pr-3 text-sm text-foreground focus:border-accent"
              />
            </div>
          </label>
          {error && <p className="text-xs text-sell">{error}</p>}
          <button
            type="submit"
            disabled={loading}
            className="min-h-11 w-full cursor-pointer rounded-lg bg-accent px-4 py-2.5 text-sm font-medium text-accent-foreground transition-colors hover:bg-accent-hover disabled:cursor-not-allowed disabled:opacity-50"
          >
            {loading ? "Signing in…" : "Sign In"}
          </button>
        </form>
      </div>
    </div>
  );
}
