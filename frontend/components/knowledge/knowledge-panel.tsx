"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  BookOpen,
  CheckCircle2,
  FileText,
  Loader2,
  Search,
  Trash2,
  Upload,
} from "lucide-react";
import {
  clearKnowledge,
  getKnowledge,
  ingestText,
  queryKnowledge,
  uploadKnowledgePdf,
} from "@/lib/api";
import type { KnowledgeChunk, KnowledgeStats } from "@/types/pipeline";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button, buttonVariants } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

export function KnowledgePanel() {
  const [stats, setStats] = useState<KnowledgeStats | null>(null);
  const [statsError, setStatsError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState<{ ok: boolean; text: string } | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const [query, setQuery] = useState("");
  const [searching, setSearching] = useState(false);
  const [results, setResults] = useState<KnowledgeChunk[] | null>(null);
  const [queryError, setQueryError] = useState<string | null>(null);

  const refreshStats = useCallback(async () => {
    try {
      setStats(await getKnowledge());
      setStatsError(null);
    } catch (err) {
      setStatsError(err instanceof Error ? err.message : "Failed to load knowledge base.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refreshStats();
  }, [refreshStats]);

  async function handleIngestText() {
    if (!text.trim()) return;
    setBusy(true);
    setNotice(null);
    try {
      const r = await ingestText(text.trim());
      setText("");
      setNotice({ ok: true, text: `Indexed ${r.chunks} chunk(s) from pasted text.` });
      refreshStats();
    } catch (err) {
      setNotice({ ok: false, text: err instanceof Error ? err.message : "Ingest failed." });
    } finally {
      setBusy(false);
    }
  }

  async function handleFile(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (fileRef.current) fileRef.current.value = ""; // allow re-selecting the same file
    if (!file) return;
    setBusy(true);
    setNotice(null);
    try {
      const r = await uploadKnowledgePdf(file);
      setNotice({ ok: true, text: `Indexed ${r.chunks} chunk(s) from ${r.pages} page(s).` });
      refreshStats();
    } catch (err) {
      setNotice({ ok: false, text: err instanceof Error ? err.message : "Upload failed." });
    } finally {
      setBusy(false);
    }
  }

  async function handleClear() {
    if (!window.confirm("Wipe the entire knowledge base?")) return;
    setBusy(true);
    setNotice(null);
    try {
      await clearKnowledge();
      setResults(null);
      setNotice({ ok: true, text: "Knowledge base cleared." });
      refreshStats();
    } catch (err) {
      setNotice({ ok: false, text: err instanceof Error ? err.message : "Clear failed." });
    } finally {
      setBusy(false);
    }
  }

  async function handleQuery(e: React.FormEvent) {
    e.preventDefault();
    if (!query.trim()) return;
    setSearching(true);
    setQueryError(null);
    try {
      const r = await queryKnowledge(query.trim());
      setResults(r.results);
    } catch (err) {
      setQueryError(err instanceof Error ? err.message : "Query failed.");
      setResults(null);
    } finally {
      setSearching(false);
    }
  }

  const chunks = stats?.total_chunks ?? 0;

  return (
    <div className="flex flex-col gap-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <BookOpen className="size-4 text-primary" />
            Company knowledge
          </CardTitle>
          <CardDescription>
            The agent grounds every decision in this. Upload a company PDF or paste a description.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-5">
          {loading ? (
            <Skeleton className="h-16 w-full" />
          ) : statsError ? (
            <p className="text-sm text-red-300">{statsError}</p>
          ) : (
            <div className="grid grid-cols-3 gap-3">
              <Stat label="Chunks indexed" value={String(chunks)} />
              <Stat label="Collection" value={stats?.collection ?? "—"} mono />
              <Stat label="Embedding model" value={stats?.embedding_model ?? "—"} mono />
            </div>
          )}

          {stats && stats.sources.length > 0 && (
            <div>
              <p className="mb-1.5 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                Sources
              </p>
              <div className="flex flex-wrap gap-1.5">
                {stats.sources.map((s) => (
                  <span
                    key={s}
                    className="inline-flex items-center gap-1.5 rounded-full bg-secondary px-2.5 py-0.5 text-xs text-secondary-foreground"
                  >
                    <FileText className="size-3" />
                    {s}
                  </span>
                ))}
              </div>
            </div>
          )}

          <div className="flex flex-col gap-2">
            <Textarea
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder="Paste your company description — what you sell, your services, your customers…"
              rows={4}
            />
            <div className="flex flex-wrap items-center gap-2">
              <Button onClick={handleIngestText} disabled={busy || !text.trim()} size="sm">
                {busy ? <Loader2 className="animate-spin" /> : <BookOpen />}
                Ingest text
              </Button>

              <label
                className={cn(
                  buttonVariants({ variant: "outline", size: "sm" }),
                  "cursor-pointer",
                  busy && "pointer-events-none opacity-60",
                )}
              >
                <Upload className="size-4" />
                Upload PDF
                <input
                  ref={fileRef}
                  type="file"
                  accept="application/pdf,.pdf"
                  className="hidden"
                  onChange={handleFile}
                  disabled={busy}
                />
              </label>

              {chunks > 0 && (
                <button
                  onClick={handleClear}
                  disabled={busy}
                  className="ml-auto inline-flex items-center gap-1.5 text-xs text-muted-foreground transition-colors hover:text-red-300 disabled:opacity-60"
                >
                  <Trash2 className="size-3.5" /> Clear
                </button>
              )}
            </div>

            {notice && (
              <p
                className={cn(
                  "text-sm",
                  notice.ok ? "text-emerald-300" : "text-red-300",
                )}
              >
                {notice.ok && <CheckCircle2 className="mr-1 inline size-3.5" />}
                {notice.text}
              </p>
            )}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Search className="size-4 text-primary" />
            Ask the knowledge base
          </CardTitle>
          <CardDescription>
            See exactly what the agent retrieves and cites for a question.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          <form onSubmit={handleQuery} className="flex gap-2">
            <Input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="e.g. what services do we offer?"
            />
            <Button type="submit" disabled={searching || !query.trim()}>
              {searching ? <Loader2 className="animate-spin" /> : <Search />}
              Search
            </Button>
          </form>

          {queryError && <p className="text-sm text-red-300">{queryError}</p>}

          {results && (
            <div className="flex flex-col gap-2">
              {results.length === 0 ? (
                <p className="text-sm text-muted-foreground">No matching chunks.</p>
              ) : (
                results.map((c, i) => (
                  <div key={i} className="rounded-lg border border-border bg-background/40 p-3">
                    <div className="mb-1.5 flex items-center justify-between gap-2 text-[11px] text-muted-foreground">
                      <span className="truncate">
                        {c.source ?? "unknown"}
                        {c.page != null && ` · p.${c.page}`}
                      </span>
                      {c.score != null && (
                        <span className="shrink-0 rounded-full bg-primary/15 px-2 py-0.5 font-medium text-primary">
                          {Math.round(c.score * 100)}% match
                        </span>
                      )}
                    </div>
                    <p className="text-sm leading-relaxed text-foreground/90">{c.text}</p>
                  </div>
                ))
              )}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function Stat({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="rounded-lg border border-border bg-background/40 p-3">
      <p
        className={cn(
          "truncate text-lg font-semibold",
          mono && "font-mono text-sm",
        )}
        title={value}
      >
        {value}
      </p>
      <p className="mt-0.5 text-xs text-muted-foreground">{label}</p>
    </div>
  );
}
