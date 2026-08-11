import type { LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

interface MetricCardProps {
  label: string;
  value: string | number;
  sub?: string;
  icon?: LucideIcon;
  tone?: "default" | "buy" | "sell" | "accent";
}

const toneStyles: Record<NonNullable<MetricCardProps["tone"]>, string> = {
  default: "text-foreground",
  buy: "text-buy",
  sell: "text-sell",
  accent: "text-accent",
};

const iconToneStyles: Record<NonNullable<MetricCardProps["tone"]>, string> = {
  default: "bg-surface-2 text-muted",
  buy: "bg-buy-soft text-buy",
  sell: "bg-sell-soft text-sell",
  accent: "bg-accent-soft text-accent",
};

export function MetricCard({ label, value, sub, icon: Icon, tone = "default" }: MetricCardProps) {
  return (
    <div className="rounded-xl border border-border bg-surface p-4 transition-colors duration-150 hover:border-border-strong">
      <div className="flex items-center justify-between">
        <p className="text-xs font-medium uppercase tracking-wide text-muted">{label}</p>
        {Icon && (
          <span className={cn("flex h-7 w-7 items-center justify-center rounded-md", iconToneStyles[tone])}>
            <Icon className="h-4 w-4" strokeWidth={2.25} />
          </span>
        )}
      </div>
      <p className={cn("mt-2 font-mono-num text-2xl font-semibold", toneStyles[tone])}>{value}</p>
      {sub && <p className="mt-0.5 text-xs text-muted-2">{sub}</p>}
    </div>
  );
}
