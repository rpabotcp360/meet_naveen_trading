import { History, Zap } from "lucide-react";
import { cn } from "@/lib/utils";

interface AlertTypeBadgeProps {
  isRealtime?: boolean;
  className?: string;
}

export function AlertTypeBadge({ isRealtime = true, className }: AlertTypeBadgeProps) {
  if (isRealtime) {
    return (
      <span
        title="Detected live as it happened"
        className={cn("inline-flex items-center gap-1 rounded-full bg-accent-soft px-2 py-0.5 text-[11px] font-medium text-accent", className)}
      >
        <Zap className="h-3 w-3" strokeWidth={2.5} />
        Realtime Alert
      </span>
    );
  }
  return (
    <span
      title="Found by reviewing today's earlier candles after the scanner started"
      className={cn("inline-flex items-center gap-1 rounded-full bg-surface-2 px-2 py-0.5 text-[11px] font-medium text-muted", className)}
    >
      <History className="h-3 w-3" strokeWidth={2.5} />
      Past Alert
    </span>
  );
}
