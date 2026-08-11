import { cn } from "@/lib/utils";

interface ConnectionBadgeProps {
  label: string;
  state: "live" | "reconnecting" | "offline" | "connected" | "disconnected" | string;
}

const stateStyles: Record<string, { pill: string; dot: string; text: string; pulse?: boolean }> = {
  live: { pill: "bg-buy-soft text-buy", dot: "bg-buy", text: "Live", pulse: true },
  connected: { pill: "bg-buy-soft text-buy", dot: "bg-buy", text: "Connected" },
  reconnecting: { pill: "bg-warning-soft text-warning", dot: "bg-warning", text: "Reconnecting", pulse: true },
  offline: { pill: "bg-surface-2 text-muted", dot: "bg-muted-2", text: "Offline" },
  disconnected: { pill: "bg-sell-soft text-sell", dot: "bg-sell", text: "Disconnected" },
};

export function ConnectionBadge({ label, state }: ConnectionBadgeProps) {
  const s = stateStyles[state] || stateStyles.offline;
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 whitespace-nowrap rounded-full px-2.5 py-1 text-xs font-medium",
        s.pill
      )}
    >
      <span className="relative flex h-1.5 w-1.5 shrink-0">
        {s.pulse && <span className={cn("absolute inline-flex h-full w-full animate-ping rounded-full opacity-60", s.dot)} />}
        <span className={cn("relative inline-flex h-1.5 w-1.5 rounded-full", s.dot)} />
      </span>
      {label}: {s.text}
    </span>
  );
}
