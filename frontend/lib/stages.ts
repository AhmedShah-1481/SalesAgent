import { PIPELINE_STAGES, type Pipeline, type PipelineStage } from "@/types/pipeline";

export interface StageStyle {
  /** Full class string for a pill/badge: bg + text + ring. */
  badge: string;
  /** Background class for a small status dot. */
  dot: string;
  /** Text color class. */
  text: string;
  /** CSS color for Recharts fills. */
  chart: string;
}

/** One curated hue per stage — neutral start → teal core → emerald win, red for dead ends. */
export const STAGE_STYLES: Record<PipelineStage, StageStyle> = {
  Discovered: {
    badge: "bg-zinc-400/10 text-zinc-300 ring-zinc-400/25",
    dot: "bg-zinc-400",
    text: "text-zinc-300",
    chart: "#a1a1aa",
  },
  Potential: {
    badge: "bg-sky-400/10 text-sky-300 ring-sky-400/25",
    dot: "bg-sky-400",
    text: "text-sky-300",
    chart: "#38bdf8",
  },
  Researching: {
    badge: "bg-violet-400/10 text-violet-300 ring-violet-400/25",
    dot: "bg-violet-400",
    text: "text-violet-300",
    chart: "#a78bfa",
  },
  Qualified: {
    badge: "bg-teal-400/10 text-teal-300 ring-teal-400/25",
    dot: "bg-teal-400",
    text: "text-teal-300",
    chart: "#2dd4bf",
  },
  Contacted: {
    badge: "bg-blue-400/10 text-blue-300 ring-blue-400/25",
    dot: "bg-blue-400",
    text: "text-blue-300",
    chart: "#60a5fa",
  },
  Interested: {
    badge: "bg-amber-400/10 text-amber-300 ring-amber-400/25",
    dot: "bg-amber-400",
    text: "text-amber-300",
    chart: "#fbbf24",
  },
  "Meeting Scheduled": {
    badge: "bg-fuchsia-400/10 text-fuchsia-300 ring-fuchsia-400/25",
    dot: "bg-fuchsia-400",
    text: "text-fuchsia-300",
    chart: "#e879f9",
  },
  Converted: {
    badge: "bg-emerald-400/15 text-emerald-300 ring-emerald-400/30",
    dot: "bg-emerald-400",
    text: "text-emerald-300",
    chart: "#34d399",
  },
  "Not Qualified": {
    badge: "bg-zinc-500/10 text-zinc-400 ring-zinc-500/20",
    dot: "bg-zinc-500",
    text: "text-zinc-400",
    chart: "#71717a",
  },
  "Not Interested": {
    badge: "bg-rose-500/10 text-rose-300 ring-rose-500/25",
    dot: "bg-rose-500",
    text: "text-rose-300",
    chart: "#fb7185",
  },
  "Do Not Contact": {
    badge: "bg-red-500/10 text-red-300 ring-red-500/25",
    dot: "bg-red-500",
    text: "text-red-300",
    chart: "#ef4444",
  },
};

const FALLBACK: StageStyle = STAGE_STYLES.Discovered;

export function stageStyle(stage: string): StageStyle {
  return STAGE_STYLES[stage as PipelineStage] ?? FALLBACK;
}

/** Counts for the eight positive stages, in lifecycle order (for the funnel chart). */
export function funnelData(pipeline: Pipeline) {
  return PIPELINE_STAGES.map((stage) => ({
    stage,
    short: stage === "Meeting Scheduled" ? "Meeting" : stage,
    count: pipeline[stage]?.length ?? 0,
    fill: STAGE_STYLES[stage].chart,
  }));
}
