"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import {
  Activity,
  HelpCircle,
  History,
  LayoutDashboard,
  List,
  LogOut,
  Radio,
  Settings,
  TrendingUp,
} from "lucide-react";
import { clearToken } from "@/lib/auth";
import { apiFetch, cn } from "@/lib/utils";
import { ConnectionBadge } from "./ConnectionBadge";

const nav = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/scanner", label: "Scanner", icon: Radio },
  { href: "/watchlist", label: "Watch List", icon: List },
  { href: "/history", label: "History", icon: History },
  { href: "/settings", label: "Settings", icon: Settings },
  { href: "/status", label: "Status", icon: Activity },
  { href: "/help", label: "Help", icon: HelpCircle },
];

function useIstClock() {
  const [istTime, setIstTime] = useState<string | null>(null);

  useEffect(() => {
    const tick = () =>
      setIstTime(
        new Date().toLocaleTimeString("en-IN", {
          timeZone: "Asia/Kolkata",
          hour: "2-digit",
          minute: "2-digit",
        })
      );
    tick();
    const interval = setInterval(tick, 15_000);
    return () => clearInterval(interval);
  }, []);

  return istTime;
}

async function handleLogout() {
  try {
    await apiFetch("/api/v1/auth/logout", { method: "POST" });
  } catch {
    /* even if the request fails, still clear the local session */
  }
  clearToken();
  window.location.href = "/login";
}

function Brand() {
  return (
    <div className="flex items-center gap-3">
      <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-accent-soft text-accent">
        <TrendingUp className="h-5 w-5" strokeWidth={2.25} />
      </span>
      <div className="min-w-0">
        <h1 className="truncate text-sm font-semibold leading-tight text-foreground">NSE Intraday Scanner</h1>
      </div>
    </div>
  );
}

interface AppShellProps {
  children: React.ReactNode;
  wsState?: "live" | "reconnecting" | "offline";
}

export function AppShell({ children, wsState = "offline" }: AppShellProps) {
  const pathname = usePathname();
  const istTime = useIstClock();

  return (
    <div className="flex h-dvh overflow-hidden bg-background">
      {/* Desktop sidebar — fixed, does not scroll with page content */}
      <aside className="hidden w-64 shrink-0 flex-col overflow-y-auto border-r border-border bg-surface md:flex">
        <div className="px-5 py-5">
          <Brand />
          <p className="font-mono-num mt-2 text-[11px] leading-tight text-muted-2">{istTime || "--:--"} IST · NSE</p>
        </div>
        <nav className="flex-1 space-y-1 px-3">
          {nav.map(({ href, label, icon: Icon }) => {
            const active = pathname === href;
            return (
              <Link
                key={href}
                href={href}
                aria-current={active ? "page" : undefined}
                className={cn(
                  "flex min-h-11 items-center gap-2.5 rounded-md px-3 py-2.5 text-sm font-medium transition-colors duration-150",
                  active ? "bg-accent-soft text-accent" : "text-muted hover:bg-surface-2 hover:text-foreground"
                )}
              >
                <Icon className="h-4 w-4 shrink-0" strokeWidth={2} />
                {label}
              </Link>
            );
          })}
        </nav>
        <div className="space-y-2 border-t border-border p-3">
          <ConnectionBadge label="Live Feed" state={wsState} />
          <button
            onClick={handleLogout}
            className="flex min-h-11 w-full cursor-pointer items-center gap-2.5 rounded-md px-3 py-2.5 text-sm font-medium text-muted transition-colors hover:bg-sell-soft hover:text-sell"
          >
            <LogOut className="h-4 w-4 shrink-0" strokeWidth={2} />
            Log out
          </button>
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col overflow-hidden">
        {/* Mobile header + horizontally-scrolling nav — fixed, does not scroll with page content */}
        <header className="shrink-0 border-b border-border bg-surface/80 backdrop-blur-md md:hidden">
          <div className="flex items-center justify-between gap-4 px-4 py-3">
            <Brand />
            <ConnectionBadge label="Live Feed" state={wsState} />
          </div>
          <nav className="flex gap-1 overflow-x-auto px-3 pb-2">
            {nav.map(({ href, label, icon: Icon }) => {
              const active = pathname === href;
              return (
                <Link
                  key={href}
                  href={href}
                  aria-current={active ? "page" : undefined}
                  className={cn(
                    "flex min-h-11 shrink-0 items-center gap-1.5 rounded-md px-3 py-2.5 text-sm font-medium transition-colors duration-150",
                    active ? "bg-accent-soft text-accent" : "text-muted hover:bg-surface-2 hover:text-foreground"
                  )}
                >
                  <Icon className="h-4 w-4" strokeWidth={2} />
                  {label}
                </Link>
              );
            })}
          </nav>
        </header>

        {/* Desktop top bar — slim, brand/nav already live in the sidebar */}
        <header className="hidden shrink-0 items-center justify-between border-b border-border bg-surface/60 px-6 py-3 md:flex">
          <p className="font-mono-num text-xs text-muted-2">{istTime || "--:--"} IST · NSE</p>
        </header>

        <main className="flex-1 overflow-y-auto px-4 py-6 sm:px-6 lg:px-8">{children}</main>
      </div>
    </div>
  );
}
