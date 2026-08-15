import Link from "next/link";
import { ArrowRight, Search, FileSearch, Filter, Send, MessageSquareReply, CalendarCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { HealthBadge } from "@/components/health-badge";
import { PIPELINE_STAGES } from "@/types/pipeline";

const CAPABILITIES = [
  {
    icon: FileSearch,
    title: "Learns your company",
    body: "Ingests your company PDF into a vector store, then grounds every decision in that knowledge.",
  },
  {
    icon: Search,
    title: "Discovers & researches leads",
    body: "Builds an ICP, finds matching companies, and deep-researches each one before spending effort.",
  },
  {
    icon: Filter,
    title: "Qualifies with a reason",
    body: "Scores fit with a confidence value and a human-readable explanation — no black boxes.",
  },
  {
    icon: Send,
    title: "Personalized outreach",
    body: "Matches the right service, finds decision-makers, and drafts tailored email / WhatsApp messages.",
  },
  {
    icon: MessageSquareReply,
    title: "Handles replies",
    body: "Classifies inbound responses and follows up automatically after 3 days of silence.",
  },
  {
    icon: CalendarCheck,
    title: "Books meetings",
    body: "Schedules a Google Meet, sends invites, and reminds the admin 30 minutes before.",
  },
];

export default function Home() {
  return (
    <div className="flex flex-col gap-16">
      {/* Hero */}
      <section className="relative -mx-6 -mt-10 overflow-hidden rounded-b-3xl border-b border-border bg-grid px-6 pb-16 pt-20">
        <div className="mx-auto max-w-3xl text-center">
          <div className="mb-6 flex justify-center">
            <Badge variant="outline" className="gap-1.5 py-1 text-muted-foreground">
              <span className="size-1.5 rounded-full bg-primary" />
              AgentHack · Autonomous AI Sales Agent
            </Badge>
          </div>
          <h1 className="font-[family-name:var(--font-display)] text-4xl font-bold tracking-tight sm:text-5xl">
            The sales rep that never sleeps,
            <span className="block text-primary">and never forgets a lead.</span>
          </h1>
          <p className="mx-auto mt-6 max-w-2xl text-balance text-lg text-muted-foreground">
            An autonomous agent that discovers prospects, researches them against your company
            knowledge, qualifies fit, reaches out, handles replies, and books meetings — end to end.
          </p>
          <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
            <Button asChild size="lg">
              <Link href="/pipeline">
                View the pipeline <ArrowRight className="size-4" />
              </Link>
            </Button>
            <Button asChild size="lg" variant="outline">
              <Link href="/knowledge">Company knowledge</Link>
            </Button>
          </div>
          <div className="mt-8 flex justify-center">
            <HealthBadge />
          </div>
        </div>
      </section>

      {/* Pipeline stages */}
      <section>
        <h2 className="mb-1 font-[family-name:var(--font-display)] text-2xl font-semibold">
          The lifecycle
        </h2>
        <p className="mb-6 text-muted-foreground">
          Every lead advances through eight stages. The agent decides each transition.
        </p>
        <div className="flex flex-wrap items-center gap-x-1 gap-y-3">
          {PIPELINE_STAGES.map((stage, i) => (
            <div key={stage} className="flex items-center gap-1">
              <span className="rounded-full border border-border bg-card px-3.5 py-1.5 text-sm font-medium">
                <span className="mr-1.5 text-xs text-primary">{String(i + 1).padStart(2, "0")}</span>
                {stage}
              </span>
              {i < PIPELINE_STAGES.length - 1 && (
                <ArrowRight className="size-4 shrink-0 text-muted-foreground/50" />
              )}
            </div>
          ))}
        </div>
      </section>

      {/* Capabilities */}
      <section>
        <h2 className="mb-6 font-[family-name:var(--font-display)] text-2xl font-semibold">
          What it does
        </h2>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {CAPABILITIES.map(({ icon: Icon, title, body }) => (
            <Card key={title} className="transition-colors hover:border-primary/40">
              <CardHeader>
                <span className="mb-2 flex size-10 items-center justify-center rounded-lg bg-primary/12 ring-1 ring-primary/25">
                  <Icon className="size-5 text-primary" />
                </span>
                <CardTitle className="text-base">{title}</CardTitle>
                <CardDescription>{body}</CardDescription>
              </CardHeader>
            </Card>
          ))}
        </div>
      </section>

      <footer className="border-t border-border pt-8 text-sm text-muted-foreground">
        Built for AgentHack · discovery → research → qualification → outreach → replies → meetings,
        fully autonomous.
      </footer>
    </div>
  );
}
