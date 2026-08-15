"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { RefreshCw } from "lucide-react";
import { getPipeline } from "@/lib/api";
import { subscribeActivity } from "@/lib/sse";
import type { ActivityEvent, Pipeline } from "@/types/pipeline";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ActivityFeed } from "@/components/activity-feed";
import { Kanban } from "./kanban";
import { PipelineFunnel } from "./funnel";
import { PipelineControls } from "./pipeline-controls";
import { cn } from "@/lib/utils";

const MAX_EVENTS = 60;

export function PipelineView() {
  const [pipeline, setPipeline] = useState<Pipeline | null>(null);
  const [events, setEvents] = useState<ActivityEvent[]>([]);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const fetchPipeline = useCallback(async () => {
    setRefreshing(true);
    try {
      const data = await getPipeline();
      setPipeline(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load the pipeline.");
    } finally {
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    fetchPipeline();

    const unsub = subscribeActivity(
      (event) => {
        setEvents((prev) => [event, ...prev].slice(0, MAX_EVENTS));
        // An event means state changed — refetch the board, debounced against bursts.
        if (debounceRef.current) clearTimeout(debounceRef.current);
        debounceRef.current = setTimeout(() => fetchPipeline(), 500);
      },
      setConnected,
    );

    // Fallback poll in case SSE is unavailable.
    const poll = setInterval(fetchPipeline, 12_000);

    return () => {
      unsub();
      clearInterval(poll);
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [fetchPipeline]);

  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="font-[family-name:var(--font-display)] text-2xl font-semibold tracking-tight">
            Pipeline
          </h1>
          <p className="mt-1 text-muted-foreground">
            Every lead, grouped by lifecycle stage — updated live as the agent works.
          </p>
        </div>
        <button
          onClick={fetchPipeline}
          disabled={refreshing}
          className="inline-flex items-center gap-2 rounded-md border border-border px-3 py-2 text-sm text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground disabled:opacity-60"
        >
          <RefreshCw className={cn("size-4", refreshing && "animate-spin")} />
          Refresh
        </button>
      </header>

      {error ? (
        <Card className="border-destructive/30">
          <CardContent className="flex flex-col items-center gap-3 py-12 text-center">
            <p className="text-sm text-red-200">{error}</p>
            <button
              onClick={fetchPipeline}
              className="inline-flex items-center gap-2 rounded-md border border-border px-3 py-2 text-sm hover:bg-secondary"
            >
              <RefreshCw className="size-4" /> Try again
            </button>
          </CardContent>
        </Card>
      ) : (
        <>
          <PipelineControls onDone={fetchPipeline} />

          <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_20rem]">
            <div className="flex min-w-0 flex-col gap-6">
              {pipeline ? <MetricsRow pipeline={pipeline} /> : <MetricsSkeleton />}

              <Card>
                <CardHeader>
                  <CardTitle className="font-[family-name:var(--font-display)] text-base">
                    Funnel
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  {pipeline ? <PipelineFunnel pipeline={pipeline} /> : <Skeleton className="h-52 w-full" />}
                </CardContent>
              </Card>

              {pipeline ? <Kanban pipeline={pipeline} /> : <KanbanSkeleton />}
            </div>

            <aside className="lg:sticky lg:top-24 h-fit">
              <Card className="p-4">
                <ActivityFeed events={events} connected={connected} className="max-h-[32rem]" />
              </Card>
            </aside>
          </div>
        </>
      )}
    </div>
  );
}

function MetricsRow({ pipeline }: { pipeline: Pipeline }) {
  const count = (stage: string) => pipeline[stage]?.length ?? 0;
  const total = Object.values(pipeline).reduce((sum, leads) => sum + leads.length, 0);
  const stats = [
    { label: "Total leads", value: total, tone: "text-foreground" },
    { label: "Qualified", value: count("Qualified"), tone: "text-teal-300" },
    { label: "Contacted", value: count("Contacted"), tone: "text-blue-300" },
    { label: "Meetings", value: count("Meeting Scheduled"), tone: "text-fuchsia-300" },
    { label: "Converted", value: count("Converted"), tone: "text-emerald-300" },
  ];
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
      {stats.map((s) => (
        <Card key={s.label} className="p-4">
          <p className={cn("font-[family-name:var(--font-display)] text-3xl font-semibold tabular-nums", s.tone)}>
            {s.value}
          </p>
          <p className="mt-1 text-xs text-muted-foreground">{s.label}</p>
        </Card>
      ))}
    </div>
  );
}

function MetricsSkeleton() {
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
      {Array.from({ length: 5 }).map((_, i) => (
        <Skeleton key={i} className="h-20 w-full" />
      ))}
    </div>
  );
}

function KanbanSkeleton() {
  return (
    <div className="flex gap-3 overflow-hidden">
      {Array.from({ length: 6 }).map((_, i) => (
        <Skeleton key={i} className="h-64 w-64 shrink-0" />
      ))}
    </div>
  );
}
