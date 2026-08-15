"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { Mail, User } from "lucide-react";
import type { Lead } from "@/types/pipeline";
import { ConfidenceMeter } from "@/components/confidence-meter";

export function LeadCard({ lead }: { lead: Lead }) {
  const topContact = lead.contacts?.[0];
  const msgCount = lead.messages?.length ?? 0;

  return (
    <motion.div
      layout
      initial={{ opacity: 0, scale: 0.97 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.18 }}
    >
      <Link
        href={`/leads/${lead.id}`}
        className="block rounded-lg border border-border bg-card/60 p-3 transition-all hover:border-primary/40 hover:bg-card hover:shadow-[0_0_16px_-8px_var(--primary)]"
      >
        <p className="truncate text-sm font-medium">{lead.company_name}</p>
        {lead.domain && <p className="truncate text-xs text-muted-foreground">{lead.domain}</p>}

        {lead.recommended_service && (
          <p className="mt-2 line-clamp-1 text-xs font-medium text-primary/90">
            {lead.recommended_service}
          </p>
        )}

        {lead.confidence != null && (
          <div className="mt-2">
            <ConfidenceMeter value={lead.confidence} />
          </div>
        )}

        {(topContact?.name || msgCount > 0) && (
          <div className="mt-2.5 flex items-center gap-3 text-[11px] text-muted-foreground">
            {topContact?.name && (
              <span className="inline-flex min-w-0 items-center gap-1">
                <User className="size-3 shrink-0" />
                <span className="truncate">{topContact.name}</span>
              </span>
            )}
            {msgCount > 0 && (
              <span className="inline-flex shrink-0 items-center gap-1">
                <Mail className="size-3" />
                {msgCount}
              </span>
            )}
          </div>
        )}
      </Link>
    </motion.div>
  );
}
