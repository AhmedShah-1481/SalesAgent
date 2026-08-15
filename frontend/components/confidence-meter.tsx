import { cn } from "@/lib/utils";

/** A compact 0–100 confidence bar, tinted by band (red → amber → teal → emerald). */
export function ConfidenceMeter({
  value,
  className,
  showLabel = true,
}: {
  value?: number | null;
  className?: string;
  showLabel?: boolean;
}) {
  if (value == null) {
    return <span className="text-xs text-muted-foreground">unscored</span>;
  }
  const pct = Math.max(0, Math.min(100, Math.round(value)));
  const tone =
    pct >= 75 ? "bg-emerald-400" : pct >= 60 ? "bg-teal-400" : pct >= 40 ? "bg-amber-400" : "bg-rose-400";
  const label =
    pct >= 75 ? "text-emerald-300" : pct >= 60 ? "text-teal-300" : pct >= 40 ? "text-amber-300" : "text-rose-300";
  return (
    <div className={cn("flex items-center gap-2", className)}>
      <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-muted">
        <div className={cn("h-full rounded-full transition-all", tone)} style={{ width: `${pct}%` }} />
      </div>
      {showLabel && <span className={cn("w-8 text-right text-xs font-semibold tabular-nums", label)}>{pct}</span>}
    </div>
  );
}
