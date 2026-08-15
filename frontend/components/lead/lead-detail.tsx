"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  ArrowLeft,
  CalendarCheck,
  ExternalLink,
  FileSearch,
  Gauge,
  Globe,
  Linkedin,
  ListChecks,
  Loader2,
  Mail,
  MessageCircle,
  MessagesSquare,
  Phone,
  Send,
  Sparkles,
  Users,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { ApiError, getLead, listMeetings, scheduleMeeting, sendReply } from "@/lib/api";
import type { Contact, Lead, Meeting, Message } from "@/types/pipeline";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Skeleton } from "@/components/ui/skeleton";
import { StageBadge } from "@/components/stage-badge";
import { ConfidenceMeter } from "@/components/confidence-meter";
import { ScoreChart } from "@/components/lead/score-chart";
import { formatDateTime, relativeTime } from "@/lib/format";
import { cn } from "@/lib/utils";

function withHttp(url: string) {
  return /^https?:\/\//i.test(url) ? url : `https://${url}`;
}

export function LeadDetail({ id }: { id: string }) {
  const [lead, setLead] = useState<Lead | null>(null);
  const [meeting, setMeeting] = useState<Meeting | null>(null);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const [l, meetings] = await Promise.all([getLead(id), listMeetings().catch(() => [])]);
      setLead(l);
      setMeeting(meetings.find((m) => m.lead_id === id) ?? null);
      setError(null);
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) setNotFound(true);
      else setError(err instanceof Error ? err.message : "Failed to load lead.");
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    load();
  }, [load]);

  if (loading) return <LeadSkeleton />;
  if (notFound) return <NotFound id={id} />;
  if (error || !lead) {
    return (
      <div className="flex flex-col gap-4">
        <BackLink />
        <Card className="border-destructive/30">
          <CardContent className="py-10 text-center text-sm text-red-200">{error}</CardContent>
        </Card>
      </div>
    );
  }

  const research = lead.research;

  return (
    <div className="flex flex-col gap-6">
      <BackLink />

      {/* Header */}
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0">
          <div className="mb-2">
            <StageBadge stage={lead.stage} />
          </div>
          <h1 className="font-[family-name:var(--font-display)] text-3xl font-semibold tracking-tight">
            {lead.company_name}
          </h1>
          {lead.domain && (
            <a
              href={withHttp(lead.domain)}
              target="_blank"
              rel="noreferrer"
              className="mt-1 inline-flex items-center gap-1.5 text-sm text-muted-foreground transition-colors hover:text-primary"
            >
              <Globe className="size-3.5" />
              {lead.domain}
            </a>
          )}
        </div>
        {lead.confidence != null && (
          <div className="min-w-52 rounded-xl border border-border bg-card p-4">
            <p className="text-xs text-muted-foreground">Qualification confidence</p>
            <div className="mt-1 flex items-center gap-3">
              <span className="font-[family-name:var(--font-display)] text-4xl font-semibold tabular-nums">
                {Math.round(lead.confidence)}
              </span>
              <ConfidenceMeter value={lead.confidence} showLabel={false} className="flex-1" />
            </div>
          </div>
        )}
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Main column */}
        <div className="flex flex-col gap-6 lg:col-span-2">
          {(lead.explanation || lead.score_breakdown) && (
            <Section icon={Gauge} title="Qualification">
              {lead.explanation && (
                <p className="whitespace-pre-line text-sm leading-relaxed text-foreground/90">
                  {lead.explanation}
                </p>
              )}
              {lead.score_breakdown && (
                <div className={cn(lead.explanation && "mt-4")}>
                  <ScoreChart breakdown={lead.score_breakdown} />
                </div>
              )}
            </Section>
          )}

          {research && (
            <Section icon={FileSearch} title="Research dossier">
              <div className="flex flex-col gap-4">
                <Facet label="Summary" value={research.profile_summary} />
                <Facet label="People & departments" value={research.employees_departments} />
                <Facet label="Problems & signals" value={research.problems_signals} />
                <Facet label="Technologies" value={research.technologies} />
                <Facet label="Funding & growth" value={research.funding_growth} />
                <Facet label="News" value={research.news} />
                <Facet label="Other evidence" value={research.other_evidence} />
                {research.sources && research.sources.length > 0 && (
                  <div>
                    <FacetLabel>Sources</FacetLabel>
                    <ul className="mt-1 flex flex-col gap-1">
                      {research.sources.map((src, i) => (
                        <li key={i}>
                          <a
                            href={withHttp(src)}
                            target="_blank"
                            rel="noreferrer"
                            className="inline-flex items-center gap-1.5 text-xs text-muted-foreground transition-colors hover:text-primary"
                          >
                            <ExternalLink className="size-3 shrink-0" />
                            <span className="truncate">{src}</span>
                          </a>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </Section>
          )}

          {lead.recommended_service && (
            <Section icon={Sparkles} title="Recommended service">
              <p className="text-sm font-medium text-primary">{lead.recommended_service}</p>
              {lead.service_rationale && (
                <p className="mt-2 whitespace-pre-line text-sm leading-relaxed text-foreground/90">
                  {lead.service_rationale}
                </p>
              )}
            </Section>
          )}

          <Section icon={MessagesSquare} title="Conversation">
            <Conversation messages={lead.messages ?? []} />
            <ReplyForm id={lead.id} onSent={load} />
          </Section>
        </div>

        {/* Sidebar */}
        <div className="flex flex-col gap-6">
          <Section icon={Users} title="Decision-makers">
            {lead.contacts && lead.contacts.length > 0 ? (
              <div className="flex flex-col gap-3">
                {lead.contacts.map((c, i) => (
                  <ContactCard key={i} contact={c} />
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">
                No decision-makers found yet — run enrichment.
              </p>
            )}
          </Section>

          <MeetingPanel lead={lead} meeting={meeting} onScheduled={load} />

          {lead.evidence && lead.evidence.length > 0 && (
            <Section icon={ListChecks} title="Evidence">
              <ul className="flex flex-col gap-2">
                {lead.evidence.map((e, i) => (
                  <li key={i} className="flex gap-2 text-sm text-foreground/90">
                    <span className="mt-1.5 size-1.5 shrink-0 rounded-full bg-primary/60" />
                    <span>{e}</span>
                  </li>
                ))}
              </ul>
            </Section>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Building blocks ────────────────────────────────────
function Section({
  icon: Icon,
  title,
  children,
}: {
  icon: LucideIcon;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <Icon className="size-4 text-primary" />
          {title}
        </CardTitle>
      </CardHeader>
      <CardContent>{children}</CardContent>
    </Card>
  );
}

function FacetLabel({ children }: { children: React.ReactNode }) {
  return (
    <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">{children}</p>
  );
}

function Facet({ label, value }: { label: string; value?: string | null }) {
  if (!value) return null;
  return (
    <div>
      <FacetLabel>{label}</FacetLabel>
      <p className="mt-1 whitespace-pre-line text-sm leading-relaxed text-foreground/90">{value}</p>
    </div>
  );
}

function ContactCard({ contact }: { contact: Contact }) {
  return (
    <div className="rounded-lg border border-border bg-background/40 p-3">
      <p className="text-sm font-medium">{contact.name ?? "Unknown"}</p>
      {contact.role && <p className="text-xs text-muted-foreground">{contact.role}</p>}
      <div className="mt-2 flex flex-col gap-1 text-xs">
        {contact.email && (
          <a
            href={`mailto:${contact.email}`}
            className="inline-flex items-center gap-1.5 text-muted-foreground transition-colors hover:text-primary"
          >
            <Mail className="size-3 shrink-0" />
            <span className="truncate">{contact.email}</span>
          </a>
        )}
        {contact.phone && (
          <span className="inline-flex items-center gap-1.5 text-muted-foreground">
            <Phone className="size-3 shrink-0" />
            {contact.phone}
          </span>
        )}
        {contact.linkedin && (
          <a
            href={withHttp(contact.linkedin)}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-1.5 text-muted-foreground transition-colors hover:text-primary"
          >
            <Linkedin className="size-3 shrink-0" />
            LinkedIn
          </a>
        )}
      </div>
      {contact.relevance && (
        <p className="mt-2 text-xs italic text-muted-foreground">{contact.relevance}</p>
      )}
    </div>
  );
}

function Conversation({ messages }: { messages: Message[] }) {
  if (messages.length === 0) {
    return <p className="text-sm text-muted-foreground">No messages yet.</p>;
  }
  return (
    <div className="flex flex-col gap-3">
      {messages.map((m, i) => {
        const isAgent = m.role === "agent";
        const ChannelIcon = m.channel === "whatsapp" ? MessageCircle : Mail;
        return (
          <div key={i} className={cn("flex", isAgent ? "justify-end" : "justify-start")}>
            <div
              className={cn(
                "max-w-[85%] rounded-2xl px-3.5 py-2",
                isAgent
                  ? "bg-primary/12 ring-1 ring-inset ring-primary/20"
                  : "bg-secondary",
              )}
            >
              <div className="mb-1 flex items-center gap-1.5 text-[11px] text-muted-foreground">
                <ChannelIcon className="size-3" />
                <span className="capitalize">{m.role}</span>
                {m.category && <span>· {m.category}</span>}
                {m.timestamp && <span>· {relativeTime(m.timestamp)}</span>}
              </div>
              <p className="whitespace-pre-line text-sm text-foreground/90">{m.text}</p>
            </div>
          </div>
        );
      })}
    </div>
  );
}

function ReplyForm({ id, onSent }: { id: string; onSent: () => void }) {
  const [text, setText] = useState("");
  const [channel, setChannel] = useState("email");
  const [sending, setSending] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!text.trim()) return;
    setSending(true);
    setErr(null);
    try {
      await sendReply(id, text.trim(), channel);
      setText("");
      onSent();
    } catch (error) {
      setErr(error instanceof Error ? error.message : "Failed to send reply.");
    } finally {
      setSending(false);
    }
  }

  return (
    <form onSubmit={submit} className="mt-4 flex flex-col gap-2 border-t border-border pt-4">
      <p className="text-xs text-muted-foreground">
        Simulate an inbound reply — the agent classifies it and advances the stage.
      </p>
      <Textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="Type a prospect reply…"
        rows={2}
      />
      <div className="flex items-center justify-between gap-2">
        <select
          value={channel}
          onChange={(e) => setChannel(e.target.value)}
          className="h-9 rounded-md border border-input bg-transparent px-2 text-sm text-foreground [&>option]:bg-popover [&>option]:text-popover-foreground"
        >
          <option value="email">Email</option>
          <option value="whatsapp">WhatsApp</option>
        </select>
        <Button type="submit" size="sm" disabled={sending || !text.trim()}>
          {sending ? <Loader2 className="animate-spin" /> : <Send />}
          Send reply
        </Button>
      </div>
      {err && <p className="text-xs text-red-300">{err}</p>}
    </form>
  );
}

function MeetingPanel({
  lead,
  meeting,
  onScheduled,
}: {
  lead: Lead;
  meeting: Meeting | null;
  onScheduled: () => void;
}) {
  const [scheduling, setScheduling] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function schedule() {
    setScheduling(true);
    setErr(null);
    try {
      await scheduleMeeting(lead.id);
      onScheduled();
    } catch (error) {
      setErr(error instanceof Error ? error.message : "Failed to schedule.");
    } finally {
      setScheduling(false);
    }
  }

  if (meeting) {
    return (
      <Section icon={CalendarCheck} title="Meeting">
        <div className="flex flex-col gap-3 text-sm">
          <div>
            <FacetLabel>When</FacetLabel>
            <p className="mt-1">{formatDateTime(meeting.scheduled_time)}</p>
          </div>
          {meeting.contact_name && (
            <div>
              <FacetLabel>With</FacetLabel>
              <p className="mt-1">{meeting.contact_name}</p>
            </div>
          )}
          {meeting.meeting_link && (
            <a
              href={withHttp(meeting.meeting_link)}
              target="_blank"
              rel="noreferrer"
              className="inline-flex w-fit items-center gap-1.5 text-primary transition-colors hover:underline"
            >
              <ExternalLink className="size-3.5" /> Join link
            </a>
          )}
          {meeting.briefing && (
            <div>
              <FacetLabel>Admin briefing</FacetLabel>
              <p className="mt-1 whitespace-pre-line text-foreground/90">{meeting.briefing}</p>
            </div>
          )}
          <p className="text-xs text-muted-foreground">
            {meeting.reminder_sent ? "Reminder sent ✓" : "Reminder pending"}
          </p>
        </div>
      </Section>
    );
  }

  const canSchedule = lead.stage === "Interested";
  return (
    <Section icon={CalendarCheck} title="Meeting">
      {canSchedule ? (
        <>
          <p className="mb-3 text-sm text-muted-foreground">
            This lead is interested — book a meeting and notify the admin.
          </p>
          <Button size="sm" onClick={schedule} disabled={scheduling}>
            {scheduling ? <Loader2 className="animate-spin" /> : <CalendarCheck />}
            Schedule meeting
          </Button>
          {err && <p className="mt-2 text-xs text-red-300">{err}</p>}
        </>
      ) : (
        <p className="text-sm text-muted-foreground">
          No meeting yet — one can be booked once the lead is{" "}
          <span className="text-amber-300">Interested</span>.
        </p>
      )}
    </Section>
  );
}

// ── States ─────────────────────────────────────────────
function BackLink() {
  return (
    <Link
      href="/pipeline"
      className="inline-flex w-fit items-center gap-1.5 text-sm text-muted-foreground transition-colors hover:text-foreground"
    >
      <ArrowLeft className="size-4" /> Back to pipeline
    </Link>
  );
}

function NotFound({ id }: { id: string }) {
  return (
    <div className="flex flex-col gap-4">
      <BackLink />
      <Card>
        <CardContent className="py-12 text-center">
          <p className="text-sm text-muted-foreground">
            No lead with id <span className="font-mono text-foreground">{id}</span>.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}

function LeadSkeleton() {
  return (
    <div className="flex flex-col gap-6">
      <Skeleton className="h-5 w-32" />
      <Skeleton className="h-16 w-72" />
      <div className="grid gap-6 lg:grid-cols-3">
        <div className="flex flex-col gap-6 lg:col-span-2">
          <Skeleton className="h-48 w-full" />
          <Skeleton className="h-64 w-full" />
        </div>
        <div className="flex flex-col gap-6">
          <Skeleton className="h-40 w-full" />
          <Skeleton className="h-40 w-full" />
        </div>
      </div>
    </div>
  );
}
