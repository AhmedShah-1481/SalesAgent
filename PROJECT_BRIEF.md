# PROJECT_BRIEF.md — Tech Stack & Architecture Decisions

This file locks in our stack choices. Do not substitute paid services or
different frameworks without asking first. Everything must run on free tiers.

## High-Level Architecture
```
┌─────────────────────────────────────────────┐
│  FRONTEND — Next.js + Tailwind + shadcn/ui    │
│  Dark theme, animated Kanban pipeline view    │
└───────────────────┬───────────────────────────┘
                     │ REST / WebSocket
┌───────────────────▼───────────────────────────┐
│  BACKEND — FastAPI (Python)                    │
│  LangGraph pipeline + LangChain components     │
│  - RAG (Chroma)                                │
│  - Lead discovery / research agents            │
│  - Qualification / scoring                     │
│  - Email (Gmail API)                           │
│  - Calendar (Google Calendar API)              │
│  - Scheduling (APScheduler)                    │
│  - Memory (Supabase Postgres)                  │
└───────────────────┬───────────────────────────┘
                     │ HTTP calls out to:
        ┌────────────┼────────────┬───────────────┐
        ▼            ▼            ▼               ▼
   Tavily/Serper  Gmail API   Google Calendar  WhatsApp
   (search)                    API              microservice
                                                (Node + Baileys)
```

## Locked Tech Stack

| Layer | Choice | Notes |
|---|---|---|
| Orchestration | **LangGraph** (Python) | Owns pipeline control flow, branching, loops (follow-ups). |
| LLM toolkit | **LangChain** | Document loaders, text splitters, prompt templates, structured output parsers. Used INSIDE LangGraph nodes, not as a competing framework. |
| LLM provider | **Groq (Llama 3.3/4)** primary, **Gemini Flash** fallback | Free tier. Use LangChain's unified ChatModel interface so provider is swappable. |
| Vector store | **Chroma** | Local, free, simple. |
| Embeddings | **sentence-transformers (all-MiniLM-L6-v2)** | Free, local, no API cost. |
| PDF parsing | **PyMuPDF** via LangChain loader | For company PDF ingestion. |
| Web/company search | **Tavily** (primary), **Serper** (backup) | Free tiers. Tavily returns LLM-ready summaries — prefer it for research steps. |
| Site scraping | **Playwright** | For scraping company websites directly (team pages, about us) when search isn't enough. |
| Email | **Gmail API** | Free. Use OAuth or app password. |
| Meetings | **Google Calendar API + Google Meet** | Free. Auto-generates real meeting links + calendar invites. |
| WhatsApp | **Baileys** (Node.js, isolated microservice) | QR-auth, no Meta business verification needed. See "WhatsApp Microservice" section below. |
| Database / long-term memory | **Supabase (Postgres)** | Free tier, hosted, has a nice dashboard for judges. |
| Short-term memory | **LangGraph checkpointer** (in-memory or SQLite) | Per-conversation/task state. |
| Follow-up scheduling | **APScheduler** | 3-day follow-up trigger, 30-min-before meeting reminder. |
| Backend framework | **FastAPI** | |
| Frontend framework | **Next.js + Tailwind + shadcn/ui** (restyled, not default theme) | Dark mode default. |
| Animations | **Framer Motion** | Pipeline stage transitions, live-activity feed. |
| Charts | **Recharts** | Confidence score visualizations. |
| Company logos (frontend) | `logo.clearbit.com/{domain}` | Free, no key needed, nice visual touch. |

## WhatsApp Microservice (Important — Read Before Building)
WhatsApp integration MUST be a **separate, isolated Node.js service** using
Baileys. It must NOT be merged into the Python backend and must NOT trigger
any conversion of the rest of the project to JS/Node.

- Node service exposes:
  - `POST /send-whatsapp` — `{ to, message }` → sends via Baileys session.
  - Forwards incoming WhatsApp messages to the Python backend via
    `POST http://<python-backend>/whatsapp-incoming`.
- Python backend calls the Node service exactly like any other external API
  (plain HTTP request from a LangGraph tool node) — same pattern as calling
  Tavily or Gmail.
- Use a secondary/test WhatsApp number for the Baileys session, not a
  personal daily-driver number.
- Store Baileys auth session files locally (`useMultiFileAuthState`) so
  reconnects don't require re-scanning the QR code every restart.

## Frontend Design Direction
- **Dark mode by default.** One intentional accent color (e.g. electric
  teal or violet) used sparingly for scores/active states — not default
  Tailwind blue.
- **Typography**: Inter or a distinctive geometric sans for headers, paired
  with a readable body font. Do not leave default system font.
- **Hero screen**: animated Kanban pipeline
  (Discovered → Potential → Researching → Qualified → Contacted → Interested
  → Meeting Scheduled → Converted), cards with circular lead-score rings and
  company logos, animated transitions between stages (Framer Motion).
- **Lead detail panel**: shows AI reasoning — score breakdown, evidence
  snippets, matched service, generated email draft. This is what proves
  "correct decisions" and "grounded personalization" to judges — do not skip.
- **Live activity feed**: scrolling log of agent actions in near-real-time
  ("Researching ABC Logistics...", "Qualified — 92%", "Email sent to CTO").
- **RAG / company knowledge view**: shows what was extracted from the
  uploaded company PDF (services, ICP, case studies) — builds trust that
  downstream decisions are grounded, not hallucinated.
- Avoid: default shadcn gray palette untouched, stock dashboard icons,
  empty/lorem-ipsum states in the demo.

## Environment Variables Needed (build `.env.example` with these keys)
```
GROQ_API_KEY=
GOOGLE_API_KEY=              # Gemini fallback + Calendar API
TAVILY_API_KEY=
SERPER_API_KEY=
GMAIL_CLIENT_ID=
GMAIL_CLIENT_SECRET=
GMAIL_REFRESH_TOKEN=
GOOGLE_CALENDAR_CREDENTIALS=
SUPABASE_URL=
SUPABASE_KEY=
WHATSAPP_SERVICE_URL=http://localhost:3001
```

## Build Order (Phased — do not build everything at once)
1. Repo scaffolding (backend + frontend + whatsapp-service folders, `.env.example`)
2. RAG layer — PDF ingestion → Chroma → retrieval, verify it answers questions
   about the uploaded company correctly before moving on
3. ICP intake + Lead Discovery (search + cheap filtering)
4. Deep Research + Qualification (confidence score + explanation)
5. Service Matching + Decision-Maker Identification
6. Personalized Outreach + Gmail send + meeting link generation
7. Response Classification + Follow-Up scheduling (APScheduler)
8. Meeting automation + admin reminders
9. WhatsApp microservice (Baileys) — isolated, wired in last
10. Memory persistence (Supabase) + Sales Pipeline state across full lifecycle
11. Frontend — Kanban pipeline, lead detail panel, activity feed, RAG view
12. End-to-end test run + polish for demo video

Confirm each phase works before starting the next. Do not skip ahead.
