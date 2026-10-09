Deployed Frontend link : https://agent-hack-self.vercel.app/
# Autonomous AI Sales Agent

An autonomous agent that runs the full B2B sales lifecycle end-to-end: it learns your company
from a PDF, builds an ideal-customer profile, discovers and researches prospects, qualifies them
with an explainable score, matches the right service, finds decision-makers, sends personalized
outreach over email and WhatsApp, classifies replies, follows up automatically, and books meetings.



> **Status: complete.** All challenge features are built and working: company knowledge/RAG (§1),
> ICP intake (§2), staged lead discovery (§3), per-lead deep research (§4), confidence-scored
> qualification (§5), RAG-grounded service matching (§6), decision-maker identification (§7),
> role-specific outreach with email send/simulate + logging (§8–9), inbound-reply classification
> (§10), automated 3-day follow-up (§11), meeting finalization with prospect confirmation + a
> 30-min admin briefing reminder (§12), live WhatsApp for admin notifications + inbound forwarding
> (§18), and **durable long-term memory** — the full pipeline (ICP, leads, contacts, emails,
> replies, objections, scores, follow-ups, meetings, final status) persists to Supabase Postgres so
> state survives restarts (§13–14), falling back to an in-memory store when `SUPABASE_*` is unset.
> A dark, real-time **dashboard** (Kanban pipeline, lead dossiers, knowledge/ICP management) drives
> the whole flow from the browser.

---

## Architecture

Three independent services. The Python backend is the brain; the other two are peripherals it
talks to over plain HTTP.

```
                         ┌──────────────────────────┐
   Browser ──HTTP/SSE──▶ │  frontend/  (Next.js)     │
                         │  dark dashboard, port 3000│
                         └────────────┬─────────────┘
                                      │ HTTP + SSE
                                      ▼
                         ┌──────────────────────────┐      ┌───────────────────────┐
                         │  backend/   (FastAPI)     │◀────▶│ Groq / Gemini (LLM)   │
                         │  LangGraph pipeline       │      │ Tavily / Serper       │
                         │  RAG · memory · scheduler │      │ Gmail · Calendar/Meet │
                         │  port 8000                │      │ Supabase (Postgres)   │
                         └────────────┬─────────────┘      └───────────────────────┘
                            send │        ▲ inbound
                                 ▼        │ webhook
                         ┌──────────────────────────┐
                         │ whatsapp-service/ (Node)  │
                         │ Baileys + Express         │
                         │ ISOLATED — port 3001      │
                         └──────────────────────────┘
```

**Why WhatsApp is a separate Node service:** Baileys is a JS-only WhatsApp library. Rather than
convert the Python project to JS, it stays a standalone microservice with exactly two HTTP seams —
Python → `POST /send-whatsapp` (outbound) and Node → `POST /whatsapp-incoming` (inbound). The
backend treats it like any other external API (Tavily, Gmail). No shared code, deps, or runtime.

### Tech stack (locked)

| Layer | Choice |
| --- | --- |
| Backend | FastAPI, LangGraph (orchestration) + LangChain (components) |
| LLM | Groq (Llama 3.3/4) primary, Gemini Flash fallback — swappable via `.with_fallbacks()` |
| RAG | Chroma + `sentence-transformers` (all-MiniLM-L6-v2), PyMuPDF |
| Research | Tavily (primary) / Serper (backup), Playwright (scraping) |
| Email / meetings | Gmail API, Google Calendar + Meet |
| Memory | LangGraph checkpointer (short-term) + Supabase Postgres (long-term) |
| Scheduling | APScheduler (3-day follow-up, 30-min meeting reminder) |
| Frontend | Next.js (App Router), Tailwind v4, shadcn/ui, Framer Motion, Recharts |
| WhatsApp | Node.js, `@whiskeysockets/baileys`, Express |

Everything runs on free tiers.

---

## Prerequisites

- **Python 3.12** (not 3.13 — for prebuilt ML wheels)
- **Node.js ≥ 20**
- API keys (see [Environment](#environment)) — none required to boot the API; two (Groq + Tavily) unlock the full demo.

---

## Setup

### 0. Environment

Copy the example env file and fill in whatever keys you have. The app boots with all keys blank.

```bash
cp .env.example .env
cp frontend/.env.local.example frontend/.env.local
```

The root `.env` is the single source of truth — the backend reads it via pydantic-settings and the
WhatsApp service reads it via dotenv. The frontend only needs `NEXT_PUBLIC_API_URL`.

**Minimum keys to run the full demo end-to-end** — just two:

- `GROQ_API_KEY` — every LLM step (discovery, research, qualification, matching, outreach, reply
  classification). Free at <https://console.groq.com>.
- `TAVILY_API_KEY` — web search for discovery + deep research. Free at <https://tavily.com>.
  (`SERPER_API_KEY` is an optional backup search provider.)

The defaults keep everything else free and offline: `EMAIL_MODE=simulate` (no Gmail),
`MEETING_MODE=simulate` (no Google Calendar), `MEMORY_BACKEND=auto` → in-memory (no Supabase). The
WhatsApp service is optional — admin notifications degrade to a log until you connect a number.

### 1. Backend — FastAPI (port 8000)

```bash
cd backend
py -3.12 -m venv .venv
source .venv/Scripts/activate      # Git Bash on Windows
# PowerShell:  .\.venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate

pip install -r requirements-base.txt   # FastAPI + LangGraph — boots the API
pip install -r requirements-ml.txt     # torch + sentence-transformers + chromadb — powers RAG (§1) & service matching (§6)
uvicorn app.main:app --reload
```

Check: <http://localhost:8000/health> → `{"status":"ok", ...}` · docs at `/docs`.

> **Both requirement files are needed for the full app.** `requirements-base.txt` alone boots the
> API (ML imports are lazy), but the RAG features — company-knowledge ingest/query (§1) and
> RAG-grounded service matching (§6) — need `requirements-ml.txt`. The first knowledge request
> downloads the `all-MiniLM-L6-v2` embedding model (~80 MB) once from Hugging Face, so the initial
> ingest takes a few extra seconds and needs network access. Deep-research website scraping (§4)
> uses a plain HTTP fetch and degrades gracefully, so **no `playwright install` step is required.**

### 2. Frontend — Next.js (port 3000)

```bash
cd frontend
npm install
npm run dev
```

Open <http://localhost:3000> — a dark, teal-accented dashboard shell.

### 3. WhatsApp service — Node + Baileys (port 3001)

```bash
cd whatsapp-service
npm install
npm start
```

Check: <http://localhost:3001/health> → ok. On first start a **QR code prints in the logs** — scan
it in WhatsApp → *Linked devices* to connect a number; `health` then reports `"connected": true`.
Until connected, `POST /send-whatsapp` returns `503` and the backend degrades admin notifications
to a log (same graceful-degradation pattern as `EMAIL_MODE`/`MEETING_MODE`). Inbound messages are
forwarded to the backend's `/whatsapp-incoming` webhook, which classifies them (§10).

### 4. Long-term memory — Supabase (optional)

The backend runs fine with **no** database: it defaults to a process-local in-memory store (state
is lost on restart). To make the full pipeline durable (§13–14), create a free Supabase project,
run the schema once, and set the keys:

```bash
# In the Supabase SQL editor (or psql), paste/run:
backend/migrations/001_init.sql        # creates icp / leads / outreach_logs / meetings tables
```

Then set `SUPABASE_URL` and `SUPABASE_KEY` in the root `.env`. `MEMORY_BACKEND` controls the choice
— `auto` (default: Supabase if both keys are set, else in-memory), or force `memory` / `supabase`.
On startup the backend logs which backend is active; if Supabase is selected but unreachable, it
logs a warning and falls back to in-memory so the app still boots.

---

## Environment

All keys live in the root `.env` (see `.env.example` for inline comments):

| Key | Purpose |
| --- | --- |
| `GROQ_API_KEY` | Primary LLM |
| `GOOGLE_API_KEY` | Gemini fallback + Calendar |
| `TAVILY_API_KEY` / `SERPER_API_KEY` | Search (primary / backup) |
| `GMAIL_CLIENT_ID` / `GMAIL_CLIENT_SECRET` / `GMAIL_REFRESH_TOKEN` / `GMAIL_SENDER` | Email (OAuth) |
| `GOOGLE_CALENDAR_CREDENTIALS` | Path to Calendar creds JSON |
| `SUPABASE_URL` / `SUPABASE_KEY` | Long-term memory |
| `WHATSAPP_SERVICE_URL` / `PYTHON_BACKEND_URL` / `WHATSAPP_PORT` / `ADMIN_WHATSAPP_NUMBER` | WhatsApp wiring |
| `CHROMA_PERSIST_DIR` / `CHECKPOINT_DB_PATH` / `UPLOAD_DIR` | Backend runtime paths |
| `NEXT_PUBLIC_API_URL` | Frontend → backend (in `frontend/.env.local`) |

---

## Tests

```bash
cd backend && source .venv/Scripts/activate   # the venv from Setup step 1 (already has base + ml)
pip install -r requirements-dev.txt
pytest
```

69 tests cover every phase — RAG retrieval, discovery filtering, qualification scoring, service
matching, outreach drafting, reply classification, follow-up eligibility, meeting finalization +
reminders, the WhatsApp webhook, and Supabase-store round-trips. LLM / search / email / DB calls
are dependency-injected with fakes, so the suite runs without any API keys.

---

## Repository layout

```
backend/            FastAPI + LangGraph pipeline (own venv)
  app/graph/nodes/  one file per lifecycle stage (stubs → filled per phase)
  app/services/     one thin client per external API
  app/rag/          PyMuPDF · Chroma · embeddings (lazy-imported)
frontend/           Next.js dashboard (own node_modules)
whatsapp-service/   Baileys + Express microservice (own node_modules, isolated)
```

## Build plan

Built in 11 phases, one at a time — all complete: (1) scaffolding, (2) RAG / company knowledge,
(3) ICP + discovery, (4) deep research + qualification, (5) service matching + decision-makers,
(6) outreach + email, (7) reply classification + follow-up, (8) meetings + admin reminder,
(9) live WhatsApp, (10) long-term memory + pipeline persistence, (11) dashboard views.
