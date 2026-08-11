"use client";

import { useEffect, useState } from "react";
import { AlertTriangle } from "lucide-react";
import { API_URL } from "@/lib/utils";

export function BackendBanner() {
  const [offline, setOffline] = useState(false);

  useEffect(() => {
    let cancelled = false;

    const check = async () => {
      try {
        const res = await fetch(`${API_URL}/health`, { signal: AbortSignal.timeout(4000) });
        if (!cancelled) setOffline(!res.ok);
      } catch {
        if (!cancelled) setOffline(true);
      }
    };

    check();
    const interval = setInterval(check, 5000);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  if (!offline) return null;

  return (
    <div className="flex items-center justify-center gap-2 border-b border-warning/30 bg-warning-soft px-4 py-2 text-center text-sm text-warning">
      <AlertTriangle className="h-4 w-4 shrink-0" strokeWidth={2.25} />
      <span>
        Backend offline — on Ubuntu run{" "}
        <code className="rounded bg-surface-2 px-1.5 py-0.5 font-mono-num text-foreground">
          systemctl restart nse-scanner-backend
        </code>
        ; on Windows use{" "}
        <code className="rounded bg-surface-2 px-1.5 py-0.5 font-mono-num text-foreground">
          .\scripts\start-backend.ps1
        </code>
      </span>
    </div>
  );
}
