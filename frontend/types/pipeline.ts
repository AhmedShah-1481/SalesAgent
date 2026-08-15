// Mirrors backend app/schemas/*.py — keep string values byte-identical.

export const PIPELINE_STAGES = [
  "Discovered",
  "Potential",
  "Researching",
  "Qualified",
  "Contacted",
  "Interested",
  "Meeting Scheduled",
  "Converted",
] as const;

export const NEGATIVE_STAGES = ["Not Qualified", "Not Interested", "Do Not Contact"] as const;

export const ALL_STAGES = [...PIPELINE_STAGES, ...NEGATIVE_STAGES] as const;

export type PipelineStage =
  | (typeof PIPELINE_STAGES)[number]
  | (typeof NEGATIVE_STAGES)[number];

export type ResponseCategory =
  | "Positive/Interested"
  | "Meeting requested"
  | "Question"
  | "Pricing objection"
  | "Technical objection"
  | "Not interested"
  | "Not now"
  | "Wrong person/Referral"
  | "Other";

export interface Contact {
  name?: string | null;
  role?: string | null;
  email?: string | null;
  phone?: string | null;
  linkedin?: string | null;
  relevance?: string | null;
}

export interface ScoreBreakdown {
  icp_fit?: number | null;
  problem_fit?: number | null;
  service_fit?: number | null;
  buying_signals?: number | null;
  company_size?: number | null;
  location?: number | null;
  evidence_quality?: number | null;
}

export interface ResearchProfile {
  website?: string | null;
  profile_summary?: string | null;
  employees_departments?: string | null;
  news?: string | null;
  funding_growth?: string | null;
  technologies?: string | null;
  problems_signals?: string | null;
  other_evidence?: string | null;
  sources?: string[];
}

export interface Message {
  role: string; // "agent" | "prospect"
  channel: string; // "email" | "whatsapp"
  text: string;
  category?: ResponseCategory | null;
  timestamp?: string | null;
}

export interface Lead {
  id: string;
  company_name: string;
  domain?: string | null;
  stage: PipelineStage;
  confidence?: number | null;
  explanation?: string | null;
  score_breakdown?: ScoreBreakdown | null;
  evidence?: string[];
  research?: ResearchProfile | null;
  recommended_service?: string | null;
  service_rationale?: string | null;
  contacts?: Contact[];
  messages?: Message[];
  last_response_category?: ResponseCategory | null;
  follow_up_count?: number;
  last_outreach_at?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
}

export type Pipeline = Record<string, Lead[]>;

export interface ICP {
  location?: string | null;
  industry?: string | null;
  company_size?: string | null;
  special_targeting?: string | null;
  notes?: string | null;
}

export interface Meeting {
  lead_id?: string | null;
  company: string;
  contact_name?: string | null;
  scheduled_time?: string | null;
  meeting_link?: string | null;
  briefing?: string | null;
  reminder_sent: boolean;
}

export interface OutreachLog {
  company: string;
  contact_name?: string | null;
  role?: string | null;
  lead_score?: number | null;
  recommended_service?: string | null;
  message: string;
  evidence?: string[];
  timestamp?: string | null;
}

export interface ActivityEvent {
  kind: string;
  message: string;
  lead_id?: string | null;
  stage?: string | null;
  timestamp?: string | null;
}

export interface KnowledgeChunk {
  text: string;
  source?: string | null;
  page?: number | null;
  score?: number | null;
}

export interface QueryResult {
  query: string;
  results: KnowledgeChunk[];
}

export interface KnowledgeStats {
  collection: string;
  embedding_model: string;
  total_chunks: number;
  sources: string[];
}

export interface IngestResult {
  source: string;
  doc_type: string;
  pages: number;
  chunks: number;
  characters: number;
  ingested_at: string;
}

export interface DiscoveryResult {
  icp: ICP;
  discovered: number;
  kept: number;
  dropped: number;
  leads: Lead[];
}
