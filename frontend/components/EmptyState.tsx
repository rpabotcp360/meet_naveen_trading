import { AlertTriangle, Inbox, Loader2 } from "lucide-react";

interface EmptyStateProps {
  title: string;
  description?: string;
}

export function EmptyState({ title, description }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center gap-2 rounded-xl border border-dashed border-border bg-surface/60 p-10 text-center">
      <span className="flex h-10 w-10 items-center justify-center rounded-full bg-surface-2 text-muted">
        <Inbox className="h-5 w-5" strokeWidth={1.75} />
      </span>
      <p className="font-medium text-foreground">{title}</p>
      {description && <p className="max-w-sm text-sm text-muted">{description}</p>}
    </div>
  );
}

export function LoadingSkeleton() {
  return (
    <div className="space-y-3" role="status" aria-label="Loading">
      <div className="h-24 rounded-xl border border-border animate-shimmer" />
      <div className="h-24 rounded-xl border border-border animate-shimmer" />
    </div>
  );
}

export function Spinner({ label }: { label?: string }) {
  return (
    <div className="flex items-center gap-3 rounded-xl border border-border bg-surface px-4 py-3 text-sm text-muted">
      <Loader2 className="h-5 w-5 shrink-0 animate-spin text-accent" strokeWidth={2.25} />
      {label && <span>{label}</span>}
    </div>
  );
}

export function ErrorState({ message }: { message: string }) {
  return (
    <div className="mb-4 flex items-start gap-2.5 rounded-xl border border-sell/30 bg-sell-soft px-4 py-3 text-sm text-sell">
      <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" strokeWidth={2.25} />
      <span>{message}</span>
    </div>
  );
}
