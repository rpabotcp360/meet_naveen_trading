"use client";

import { useEffect, useState } from "react";
import { Lock, TrendingUp, User } from "lucide-react";
import { setToken } from "@/lib/auth";
import { API_URL } from "@/lib/utils";

type Mode = "login" | "signup";

async function readDetail(res: Response): Promise<string> {
  const text = await res.text();
  if (!text) return res.statusText || "Request failed";
  try {
    const data = JSON.parse(text) as { detail?: unknown };
    if (typeof data.detail === "string") return data.detail;
  } catch {
    /* plain text */
  }
  return text;
}

export default function LoginPage() {
  const [mode, setMode] = useState<Mode>("login");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [info, setInfo] = useState("");
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
        if (!cancelled) {
          const isConfigured = Boolean(data.configured);
          setConfigured(isConfigured);
          setMode(isConfigured ? "login" : "signup");
        }
      } catch {
        if (!cancelled) {
          setConfigured(true);
          setMode("login");
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const signupAllowed = configured === false;

  const switchMode = (next: Mode) => {
    if (next === "signup" && !signupAllowed) return;
    setMode(next);
    setError("");
    setInfo("");
    setPassword("");
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setInfo("");
    setLoading(true);
    try {
      if (mode === "signup") {
        const res = await fetch(`${API_URL}/api/v1/auth/signup`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ username, password }),
        });
        if (!res.ok) {
          throw new Error(await readDetail(res));
        }
        const data = (await res.json()) as { message?: string };
        setConfigured(true);
        setMode("login");
        setPassword("");
        setInfo(data.message || "Account created. Please sign in.");
        return;
      }

      const res = await fetch(`${API_URL}/api/v1/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });
      if (!res.ok) {
        throw new Error(await readDetail(res));
      }
      const data = (await res.json()) as { token: string };
      setToken(data.token);
      window.location.href = "/";
    } catch (err) {
      setError(err instanceof Error ? err.message : "Request failed");
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
                : mode === "signup"
                  ? "Create your account"
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
                disabled={configured === null}
                className="min-h-11 w-full rounded-lg border border-border bg-surface-2 py-2.5 pl-10 pr-3 text-sm text-foreground focus:border-accent disabled:opacity-50"
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
                minLength={mode === "signup" ? 6 : 1}
                autoComplete={mode === "signup" ? "new-password" : "current-password"}
                disabled={configured === null}
                className="min-h-11 w-full rounded-lg border border-border bg-surface-2 py-2.5 pl-10 pr-3 text-sm text-foreground focus:border-accent disabled:opacity-50"
              />
            </div>
          </label>
          {mode === "signup" && (
            <p className="text-xs text-muted">
              One-time signup. After this account is created, signup will be closed.
            </p>
          )}
          {info && <p className="text-xs text-buy">{info}</p>}
          {error && <p className="text-xs text-sell">{error}</p>}
          <button
            type="submit"
            disabled={loading || configured === null}
            className="min-h-11 w-full cursor-pointer rounded-lg bg-accent px-4 py-2.5 text-sm font-medium text-accent-foreground transition-colors hover:bg-accent-hover disabled:cursor-not-allowed disabled:opacity-50"
          >
            {loading
              ? mode === "signup"
                ? "Creating…"
                : "Signing in…"
              : mode === "signup"
                ? "Sign up"
                : "Sign In"}
          </button>
        </form>
        {signupAllowed && mode === "login" && (
          <p className="mt-4 text-center text-xs text-muted">
            No account yet?{" "}
            <button type="button" onClick={() => switchMode("signup")} className="cursor-pointer text-accent hover:underline">
              Sign up
            </button>
          </p>
        )}
        {mode === "signup" && (
          <p className="mt-4 text-center text-xs text-muted">
            Already created?{" "}
            <button type="button" onClick={() => switchMode("login")} className="cursor-pointer text-accent hover:underline">
              Sign in
            </button>
          </p>
        )}
      </div>
    </div>
  );
}
