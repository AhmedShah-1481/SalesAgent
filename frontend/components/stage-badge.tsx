import { cn } from "@/lib/utils";
import { stageStyle } from "@/lib/stages";

/** A colored pill for a pipeline stage, hue-coded per {@link STAGE_STYLES}. */
export function StageBadge({ stage, className }: { stage: string; className?: string }) {
  const s = stageStyle(stage);
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium ring-1 ring-inset",
        s.badge,
        className,
      )}
    >
      <span className={cn("size-1.5 rounded-full", s.dot)} />
      {stage}
    </span>
  );
}
