"use client";

import { useEffect, useState } from "react";
import { getHealth } from "@/lib/api";
import { cn } from "@/lib/utils";

type Status = "checking" | "online" | "offline";

// Small client-side probe so the landing page reflects whether FastAPI is up.
export function HealthBadge() {
  const [status, setStatus] = useState<Status>("checking");

  useEffect(() => {
    let alive = true;
    getHealth()
      .then(() => alive && setStatus("online"))
      .catch(() => alive && setStatus("offline"));
    return () => {
      alive = false;
    };
  }, []);

  const label =
    status === "checking" ? "Checking backend…" : status === "online" ? "Backend online" : "Backend offline";

  return (
    <div className="inline-flex items-center gap-2 rounded-full border border-border bg-card/60 px-3 py-1 text-xs text-muted-foreground">
      <span
        className={cn(
          "size-2 rounded-full",
          status === "online" && "bg-primary shadow-[0_0_8px_var(--primary)]",
          status === "offline" && "bg-destructive",
          status === "checking" && "animate-pulse bg-muted-foreground"
        )}
      />
      {label}
    </div>
  );
}
