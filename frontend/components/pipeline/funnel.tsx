"use client";

import { Bar, BarChart, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { Pipeline } from "@/types/pipeline";
import { funnelData } from "@/lib/stages";

export function PipelineFunnel({ pipeline }: { pipeline: Pipeline }) {
  const data = funnelData(pipeline);
  const total = data.reduce((sum, d) => sum + d.count, 0);

  if (total === 0) {
    return (
      <p className="py-10 text-center text-sm text-muted-foreground">
        No leads yet — run discovery to populate the pipeline.
      </p>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart data={data} layout="vertical" margin={{ left: 4, right: 24, top: 4, bottom: 4 }}>
        <XAxis type="number" hide allowDecimals={false} />
        <YAxis
          type="category"
          dataKey="short"
          width={108}
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
          labelStyle={{ color: "var(--color-foreground)" }}
        />
        <Bar dataKey="count" radius={4} background={{ fill: "var(--color-muted)" }} label={{ position: "right", fill: "var(--color-muted-foreground)", fontSize: 11 }}>
          {data.map((d) => (
            <Cell key={d.stage} fill={d.fill} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
