"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import {
  BellRing,
  CheckCircle2,
  Clock,
  FileSearch,
  Loader2,
  Search,
  Send,
  Sparkles,
  TriangleAlert,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import {
  discover,
  runEnrich,
  runFollowUp,
  runOutreach,
  runReminders,
  runResearch,
} from "@/lib/api";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";

interface Action {
  key: string;
  label: string;
  icon: LucideIcon;
  hint: string;
  /** Runs the step and returns a short human summary of the result. */
  exec: () => Promise<string>;
}

const ACTIONS: Action[] = [
  {
    key: "discover",
    label: "Discover",
    icon: Search,
    hint: "Find companies matching the ICP",
    exec: async () => {
      const r = await discover();
      return `Discovered ${r.discovered}, kept ${r.kept} (dropped ${r.dropped}).`;
    },
  },
  {
    key: "research",
    label: "Research + qualify",
    icon: FileSearch,
    hint: "Deep-research potentials, score fit",
    exec: async () => {
      const r = await runResearch();
      return `Researched ${r.researched}: ${r.qualified} qualified, ${r.not_qualified} not.`;
    },
  },
  {
    key: "enrich",
    label: "Match + find people",
    icon: Sparkles,
    hint: "Pick a service, find decision-makers",
    exec: async () => {
      const r = await runEnrich();
      return `Enriched ${r.enriched}: ${r.with_service} matched, ${r.with_contacts} with contacts.`;
    },
  },
  {
    key: "outreach",
    label: "Send outreach",
    icon: Send,
    hint: "Draft + send/simulate first email",
    exec: async () => {
      const r = await runOutreach();
      return `${r.emails} email(s) (${r.mode}) → ${r.contacted} contacted.`;
    },
  },
  {
    key: "followup",
    label: "Follow up",
    icon: Clock,
    hint: "Second touch to silent leads (forced)",
    exec: async () => {
      const r = await runFollowUp(true);
      return `${r.emails} follow-up(s) sent to ${r.followed_up} lead(s).`;
    },
  },
  {
    key: "reminders",
    label: "Meeting reminders",
    icon: BellRing,
    hint: "Notify admin of upcoming meetings (forced)",
    exec: async () => {
      const r = await runReminders(true);
      return `${r.reminded} reminder(s) sent, ${r.pending} pending.`;
    },
  },
];

export function PipelineControls({ onDone }: { onDone: () => void }) {
  const [running, setRunning] = useState<string | null>(null);
  const [result, setResult] = useState<{ ok: boolean; text: string } | null>(null);

  async function handle(action: Action) {
    setRunning(action.key);
    setResult(null);
    try {
      const text = await action.exec();
      setResult({ ok: true, text });
      onDone();
    } catch (err) {
      setResult({ ok: false, text: err instanceof Error ? err.message : "Something went wrong." });
    } finally {
      setRunning(null);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="font-[family-name:var(--font-display)] text-base">
          Run the pipeline
        </CardTitle>
        <CardDescription>
          Drive the agent one stage at a time. Each step acts on the leads currently in the
          matching stage — set an ICP on the Knowledge page first.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
          {ACTIONS.map((action) => {
            const isRunning = running === action.key;
            const Icon = action.icon;
            return (
              <button
                key={action.key}
                onClick={() => handle(action)}
                disabled={running !== null}
                className={cn(
                  "group flex items-start gap-3 rounded-lg border border-border bg-card/50 p-3 text-left transition-all",
                  "hover:border-primary/40 hover:bg-card disabled:cursor-not-allowed disabled:opacity-60",
                )}
              >
                <span className="mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-md bg-primary/12 text-primary ring-1 ring-primary/25 [&_svg]:size-4">
                  {isRunning ? <Loader2 className="animate-spin" /> : <Icon />}
                </span>
                <span className="min-w-0">
                  <span className="block text-sm font-medium">{action.label}</span>
                  <span className="block text-xs text-muted-foreground">{action.hint}</span>
                </span>
              </button>
            );
          })}
        </div>

        {result && (
          <motion.div
            initial={{ opacity: 0, y: -4 }}
            animate={{ opacity: 1, y: 0 }}
            className={cn(
              "flex items-start gap-2 rounded-lg border px-3 py-2 text-sm",
              result.ok
                ? "border-emerald-400/25 bg-emerald-400/10 text-emerald-200"
                : "border-destructive/25 bg-destructive/10 text-red-200",
            )}
          >
            {result.ok ? (
              <CheckCircle2 className="mt-0.5 size-4 shrink-0" />
            ) : (
              <TriangleAlert className="mt-0.5 size-4 shrink-0" />
            )}
            <span>{result.text}</span>
          </motion.div>
        )}
      </CardContent>
    </Card>
  );
}
