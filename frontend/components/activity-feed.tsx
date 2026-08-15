"use client";

import Link from "next/link";
import { AnimatePresence, motion } from "framer-motion";
import {
  Activity,
  BellRing,
  BookOpen,
  CalendarCheck,
  Clock,
  Gauge,
  MessageCircle,
  MessageSquareReply,
  Search,
  Send,
  Sparkles,
  Target,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import type { ActivityEvent } from "@/types/pipeline";
import { relativeTime } from "@/lib/format";
import { cn } from "@/lib/utils";

const KIND_META: Record<string, { icon: LucideIcon; tone: string }> = {
  knowledge: { icon: BookOpen, tone: "text-sky-300 bg-sky-400/10" },
  icp: { icon: Target, tone: "text-violet-300 bg-violet-400/10" },
  discovery: { icon: Search, tone: "text-sky-300 bg-sky-400/10" },
  qualification: { icon: Gauge, tone: "text-teal-300 bg-teal-400/10" },
  enrichment: { icon: Sparkles, tone: "text-amber-300 bg-amber-400/10" },
  outreach: { icon: Send, tone: "text-blue-300 bg-blue-400/10" },
  reply: { icon: MessageSquareReply, tone: "text-amber-300 bg-amber-400/10" },
  follow_up: { icon: Clock, tone: "text-blue-300 bg-blue-400/10" },
  whatsapp_in: { icon: MessageCircle, tone: "text-emerald-300 bg-emerald-400/10" },
  meeting: { icon: CalendarCheck, tone: "text-fuchsia-300 bg-fuchsia-400/10" },
  meeting_reminder: { icon: BellRing, tone: "text-fuchsia-300 bg-fuchsia-400/10" },
};

const FALLBACK = { icon: Activity, tone: "text-muted-foreground bg-muted" };

export function ActivityFeed({
  events,
  connected,
  className,
}: {
  events: ActivityEvent[];
  connected: boolean;
  className?: string;
}) {
  return (
    <div className={cn("flex h-full flex-col", className)}>
      <div className="mb-3 flex items-center justify-between">
        <h3 className="font-[family-name:var(--font-display)] text-sm font-semibold">
          Live activity
        </h3>
        <span className="flex items-center gap-1.5 text-xs text-muted-foreground">
          <span
            className={cn(
              "size-2 rounded-full",
              connected ? "bg-emerald-400 shadow-[0_0_8px_var(--color-chart-3)]" : "bg-zinc-500",
            )}
          />
          {connected ? "streaming" : "offline"}
        </span>
      </div>

      {events.length === 0 ? (
        <div className="flex flex-1 items-center justify-center rounded-lg border border-dashed border-border py-10 text-center text-sm text-muted-foreground">
          Waiting for the agent to act…
        </div>
      ) : (
        <ul className="flex flex-col gap-1.5 overflow-y-auto pr-1">
          <AnimatePresence initial={false}>
            {events.map((e, i) => {
              const meta = KIND_META[e.kind] ?? FALLBACK;
              const Icon = meta.icon;
              const key = `${e.timestamp ?? ""}-${e.kind}-${i}`;
              const body = (
                <div className="flex gap-2.5 rounded-lg border border-transparent p-2 transition-colors hover:border-border hover:bg-secondary/40">
                  <span
                    className={cn(
                      "mt-0.5 flex size-7 shrink-0 items-center justify-center rounded-md [&_svg]:size-3.5",
                      meta.tone,
                    )}
                  >
                    <Icon />
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="text-sm leading-snug text-foreground/90">{e.message}</p>
                    <p className="mt-0.5 text-[11px] text-muted-foreground">
                      {relativeTime(e.timestamp)}
                    </p>
                  </div>
                </div>
              );
              return (
                <motion.li
                  key={key}
                  layout
                  initial={{ opacity: 0, y: -8 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0 }}
                  transition={{ duration: 0.2 }}
                >
                  {e.lead_id ? (
                    <Link href={`/leads/${e.lead_id}`} className="block">
                      {body}
                    </Link>
                  ) : (
                    body
                  )}
                </motion.li>
              );
            })}
          </AnimatePresence>
        </ul>
      )}
    </div>
  );
}
