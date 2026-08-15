"use client";

import Link from "next/link";
import { AnimatePresence } from "framer-motion";
import {
  NEGATIVE_STAGES,
  PIPELINE_STAGES,
  type Pipeline,
} from "@/types/pipeline";
import { stageStyle } from "@/lib/stages";
import { cn } from "@/lib/utils";
import { LeadCard } from "./lead-card";

export function Kanban({ pipeline }: { pipeline: Pipeline }) {
  return (
    <div className="flex flex-col gap-5">
      <div className="flex gap-3 overflow-x-auto pb-2">
        {PIPELINE_STAGES.map((stage) => {
          const leads = pipeline[stage] ?? [];
          const s = stageStyle(stage);
          return (
            <div
              key={stage}
              className="flex w-64 shrink-0 flex-col rounded-xl border border-border bg-background/40"
            >
              <div className="flex items-center justify-between gap-2 border-b border-border px-3 py-2.5">
                <span className="flex items-center gap-2 text-sm font-medium">
                  <span className={cn("size-2 rounded-full", s.dot)} />
                  {stage}
                </span>
                <span className="rounded-full bg-muted px-2 py-0.5 text-xs tabular-nums text-muted-foreground">
                  {leads.length}
                </span>
              </div>
              <div className="flex min-h-28 flex-col gap-2 p-2">
                {leads.length === 0 ? (
                  <p className="px-1 py-8 text-center text-xs text-muted-foreground/50">empty</p>
                ) : (
                  <AnimatePresence initial={false}>
                    {leads.map((lead) => (
                      <LeadCard key={lead.id} lead={lead} />
                    ))}
                  </AnimatePresence>
                )}
              </div>
            </div>
          );
        })}
      </div>

      <NegativeStages pipeline={pipeline} />
    </div>
  );
}

function NegativeStages({ pipeline }: { pipeline: Pipeline }) {
  const present = NEGATIVE_STAGES.filter((stage) => (pipeline[stage]?.length ?? 0) > 0);
  if (present.length === 0) return null;

  return (
    <div className="rounded-xl border border-dashed border-border bg-background/30 p-4">
      <p className="mb-3 text-xs font-medium uppercase tracking-wide text-muted-foreground">
        Closed / disqualified
      </p>
      <div className="grid gap-4 sm:grid-cols-3">
        {present.map((stage) => {
          const leads = pipeline[stage] ?? [];
          const s = stageStyle(stage);
          return (
            <div key={stage}>
              <p className="mb-2 flex items-center gap-2 text-sm">
                <span className={cn("size-2 rounded-full", s.dot)} />
                <span className={s.text}>{stage}</span>
                <span className="text-muted-foreground">· {leads.length}</span>
              </p>
              <ul className="flex flex-col gap-1">
                {leads.map((lead) => (
                  <li key={lead.id}>
                    <Link
                      href={`/leads/${lead.id}`}
                      className="block truncate rounded-md px-2 py-1 text-xs text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground"
                    >
                      {lead.company_name}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          );
        })}
      </div>
    </div>
  );
}
