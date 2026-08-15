"use client";

import { useEffect, useState } from "react";
import { CheckCircle2, Loader2, Target } from "lucide-react";
import { getIcp, saveIcp } from "@/lib/api";
import type { ICP } from "@/types/pipeline";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Skeleton } from "@/components/ui/skeleton";

const FIELDS: { key: keyof ICP; label: string; placeholder: string }[] = [
  { key: "industry", label: "Industry", placeholder: "e.g. B2B logistics SaaS" },
  { key: "location", label: "Location", placeholder: "e.g. DACH region" },
  { key: "company_size", label: "Company size", placeholder: "e.g. 50–500 employees" },
  {
    key: "special_targeting",
    label: "Special targeting",
    placeholder: "e.g. recently funded, scaling operations",
  },
];

export function IcpPanel() {
  const [icp, setIcp] = useState<ICP>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    getIcp()
      .then((value) => {
        if (value) setIcp(value);
      })
      .catch(() => {
        /* leave the form empty if the backend is unreachable */
      })
      .finally(() => setLoading(false));
  }, []);

  function set(key: keyof ICP, value: string) {
    setIcp((prev) => ({ ...prev, [key]: value }));
    setSaved(false);
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setErr(null);
    try {
      const cleaned: ICP = {};
      (Object.keys(icp) as (keyof ICP)[]).forEach((k) => {
        const v = icp[k];
        if (typeof v === "string" && v.trim()) cleaned[k] = v.trim();
      });
      const result = await saveIcp(cleaned);
      setIcp(result);
      setSaved(true);
    } catch (error) {
      setErr(error instanceof Error ? error.message : "Failed to save the ICP.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <Target className="size-4 text-primary" />
          Ideal customer profile
        </CardTitle>
        <CardDescription>
          Who the agent should hunt for. Discovery uses this to find matching companies.
        </CardDescription>
      </CardHeader>
      <CardContent>
        {loading ? (
          <div className="flex flex-col gap-4">
            {Array.from({ length: 3 }).map((_, i) => (
              <Skeleton key={i} className="h-14 w-full" />
            ))}
          </div>
        ) : (
          <form onSubmit={submit} className="flex flex-col gap-4">
            {FIELDS.map((f) => (
              <div key={f.key} className="flex flex-col gap-1.5">
                <Label htmlFor={f.key}>{f.label}</Label>
                <Input
                  id={f.key}
                  value={(icp[f.key] as string) ?? ""}
                  onChange={(e) => set(f.key, e.target.value)}
                  placeholder={f.placeholder}
                />
              </div>
            ))}
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="notes">Notes</Label>
              <Textarea
                id="notes"
                value={icp.notes ?? ""}
                onChange={(e) => set("notes", e.target.value)}
                placeholder="Anything else that defines a great-fit customer…"
                rows={3}
              />
            </div>

            <div className="flex items-center gap-3">
              <Button type="submit" disabled={saving}>
                {saving ? <Loader2 className="animate-spin" /> : <Target />}
                Save ICP
              </Button>
              {saved && (
                <span className="inline-flex items-center gap-1.5 text-sm text-emerald-300">
                  <CheckCircle2 className="size-4" /> Saved
                </span>
              )}
              {err && <span className="text-sm text-red-300">{err}</span>}
            </div>
          </form>
        )}
      </CardContent>
    </Card>
  );
}
