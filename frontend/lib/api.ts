import type {
  DiscoveryResult,
  ICP,
  IngestResult,
  KnowledgeStats,
  Lead,
  Meeting,
  OutreachLog,
  Pipeline,
  QueryResult,
} from "@/types/pipeline";

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export interface HealthResponse {
  status: string;
  service: string;
  phase: string;
}

/** Error carrying the backend's `detail` string and HTTP status, so the UI can be honest. */
export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, {
      cache: "no-store",
      headers: init?.body ? { "Content-Type": "application/json" } : undefined,
      ...init,
    });
  } catch {
    throw new ApiError(`Cannot reach the backend at ${API_URL}. Is it running?`, 0);
  }
  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`;
    try {
      const body = await res.json();
      if (body?.detail) {
        detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
      }
    } catch {
      /* non-JSON error body — keep the status line */
    }
    throw new ApiError(detail, res.status);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export const apiGet = <T,>(path: string) => request<T>(path);
export const apiPost = <T,>(path: string, body?: unknown) =>
  request<T>(path, {
    method: "POST",
    body: body === undefined ? undefined : JSON.stringify(body),
  });
export const apiDelete = <T,>(path: string) => request<T>(path, { method: "DELETE" });

// ── Reads ──────────────────────────────────────────────
export const getHealth = () => apiGet<HealthResponse>("/health");
export const getPipeline = () => apiGet<Pipeline>("/pipeline");
export const listLeads = () => apiGet<Lead[]>("/leads");
export const getLead = (id: string) => apiGet<Lead>(`/leads/${encodeURIComponent(id)}`);
export const listOutreach = () => apiGet<OutreachLog[]>("/outreach");
export const listMeetings = () => apiGet<Meeting[]>("/meetings");
export const getIcp = () => apiGet<ICP | null>("/icp");
export const getKnowledge = () => apiGet<KnowledgeStats>("/knowledge");

// ── Writes: knowledge + ICP ────────────────────────────
export const saveIcp = (icp: ICP) => apiPost<ICP>("/icp", icp);
export const discover = () => apiPost<DiscoveryResult>("/icp/discover");
export const ingestText = (text: string, source?: string) =>
  apiPost<IngestResult>("/knowledge/text", { text, ...(source ? { source } : {}) });
export const queryKnowledge = (query: string, k?: number) =>
  apiPost<QueryResult>("/knowledge/query", { query, ...(k ? { k } : {}) });
export const clearKnowledge = () => apiDelete<{ status: string }>("/knowledge");

/** PDF ingest is multipart, so it bypasses the JSON `request` helper (field name: "file"). */
export async function uploadKnowledgePdf(file: File): Promise<IngestResult> {
  const form = new FormData();
  form.append("file", file);
  let res: Response;
  try {
    res = await fetch(`${API_URL}/knowledge/upload`, {
      method: "POST",
      body: form,
      cache: "no-store",
    });
  } catch {
    throw new ApiError(`Cannot reach the backend at ${API_URL}. Is it running?`, 0);
  }
  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`;
    try {
      const body = await res.json();
      if (body?.detail) detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    } catch {
      /* keep status line */
    }
    throw new ApiError(detail, res.status);
  }
  return (await res.json()) as IngestResult;
}

// ── Pipeline triggers (response shapes mirror leads.py) ─
export interface ResearchRunResult {
  researched: number;
  qualified: number;
  not_qualified: number;
  skipped: number;
  leads: Lead[];
}
export interface EnrichmentRunResult {
  enriched: number;
  with_service: number;
  with_contacts: number;
  skipped: number;
  leads: Lead[];
}
export interface OutreachRunResult {
  contacted: number;
  emails: number;
  skipped: number;
  mode: string;
  leads: Lead[];
}
export interface FollowUpRunResult {
  followed_up: number;
  emails: number;
  eligible_pool: number;
  mode: string;
  leads: Lead[];
}
export interface ReminderRunResult {
  reminded: number;
  pending: number;
  meetings: Meeting[];
}
export interface MeetingResult {
  meeting: Meeting;
  lead: Lead;
  emailed: boolean;
}

export const runResearch = () => apiPost<ResearchRunResult>("/leads/research");
export const runEnrich = () => apiPost<EnrichmentRunResult>("/leads/enrich");
export const runOutreach = () => apiPost<OutreachRunResult>("/leads/outreach");
export const runFollowUp = (force = true) =>
  apiPost<FollowUpRunResult>(`/leads/follow-up?force=${force}`);
export const runReminders = (force = true) =>
  apiPost<ReminderRunResult>(`/meetings/reminders/run?force=${force}`);
export const scheduleMeeting = (id: string) =>
  apiPost<MeetingResult>(`/leads/${encodeURIComponent(id)}/schedule-meeting`, {});
export const sendReply = (id: string, text: string, channel = "email") =>
  apiPost<{ lead: Lead }>(`/leads/${encodeURIComponent(id)}/reply`, { text, channel });
