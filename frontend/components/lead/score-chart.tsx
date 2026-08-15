"use client";

import { Bar, BarChart, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { ScoreBreakdown } from "@/types/pipeline";

const LABELS: Record<keyof ScoreBreakdown, string> = {
  icp_fit: "ICP fit",
  problem_fit: "Problem fit",
  service_fit: "Service fit",
  buying_signals: "Buying signals",
  company_size: "Company size",
  location: "Location",
  evidence_quality: "Evidence quality",
};

const ORDER = Object.keys(LABELS) as (keyof ScoreBreakdown)[];

export function ScoreChart({ breakdown }: { breakdown: ScoreBreakdown }) {
  const data = ORDER.map((k) => ({ label: LABELS[k], value: breakdown[k] })).filter(
    (d): d is { label: string; value: number } => typeof d.value === "number",
  );

  if (data.length === 0) return null;
  const max = Math.max(...data.map((d) => d.value), 1);

  return (
    <ResponsiveContainer width="100%" height={data.length * 34 + 12}>
      <BarChart data={data} layout="vertical" margin={{ left: 4, right: 32, top: 0, bottom: 0 }}>
        <XAxis type="number" hide domain={[0, max]} />
        <YAxis
          type="category"
          dataKey="label"
          width={116}
          tick={{ fill: "var(--color-muted-foreground)", fontSize: 12 }}
          axisLine={false}
          tickLine={false}
        />
        <Tooltip
          cursor={{ fill: "var(--color-muted)", opacity: 0.4 }}
          contentStyle={{
            background: "var(--color-popover)",
            border: "1px solid var(--color-border)",
            borderRadius: 8,
            fontSize: 12,
            color: "var(--color-popover-foreground)",
          }}
        />
        <Bar
          dataKey="value"
          radius={4}
          background={{ fill: "var(--color-muted)" }}
          label={{ position: "right", fill: "var(--color-muted-foreground)", fontSize: 11 }}
        >
          {data.map((d) => (
            <Cell key={d.label} fill="var(--color-chart-1)" opacity={0.55 + 0.45 * (d.value / max)} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
