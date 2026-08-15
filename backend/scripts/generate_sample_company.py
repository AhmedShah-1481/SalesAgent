"""Generate a synthetic sample company profile PDF for developing/demoing the RAG layer.

There is no organizer-provided company PDF in the repo, so this produces a realistic
fictional one — "Sable AI Solutions", a B2B AI-automation agency. Its service catalog is
designed to exercise the whole pipeline (e.g. a WhatsApp AI Chatbot service so the §6
service-matching example — "high WhatsApp inquiry volume -> recommend WhatsApp chatbot"
— has something to match against).

Run:  python scripts/generate_sample_company.py
Out:  backend/sample_data/sable_ai_company_profile.pdf   (committed to the repo)
"""
from __future__ import annotations

from pathlib import Path

OUT_PATH = Path(__file__).resolve().parent.parent / "sample_data" / "sable_ai_company_profile.pdf"

CSS = """
body { font-family: sans-serif; font-size: 10.5pt; color: #1a2b33; line-height: 1.45; }
h1 { font-size: 22pt; color: #0d7d78; margin-bottom: 2pt; }
h2 { font-size: 14pt; color: #0d7d78; margin-top: 16pt; margin-bottom: 4pt;
     border-bottom: 1px solid #7fd6cf; padding-bottom: 2pt; }
h3 { font-size: 11.5pt; color: #12545a; margin-top: 10pt; margin-bottom: 2pt; }
.subtitle { font-size: 11pt; color: #4a6068; margin-top: 0; }
.tag { font-size: 9pt; color: #4a6068; }
ul { margin-top: 2pt; }
li { margin-bottom: 2pt; }
td { padding: 3pt 8pt 3pt 0; vertical-align: top; }
th { text-align: left; color: #12545a; padding: 3pt 8pt 3pt 0; }
"""

HTML = """
<h1>Sable AI Solutions</h1>
<p class="subtitle">Applied AI automation for customer-facing teams.</p>
<p class="tag">Company profile &middot; Confidential &middot; Head office: Austin, TX &middot;
Founded 2021 &middot; 60 employees</p>

<h2>About us</h2>
<p>Sable AI Solutions is a B2B artificial-intelligence agency that designs, builds, and
operates AI automation for mid-market companies. We help revenue and support teams cut
manual workload and respond to customers faster by deploying conversational assistants,
outbound automation, and retrieval-based knowledge systems on top of our clients'
existing tools. We sell outcomes — measurable reductions in response time and cost per
conversation — not raw model access. Every engagement pairs a solutions engineer with a
customer-success lead, and we operate the systems we build rather than handing over code
and walking away.</p>

<h2>What we sell — services &amp; capabilities</h2>

<h3>1. WhatsApp AI Chatbot &amp; Conversational Support Automation</h3>
<p>An AI assistant deployed on WhatsApp Business, web chat, and Instagram DMs that answers
customer questions, qualifies inquiries, and hands off to a human when needed. Best fit for
companies with high inbound message volume. Handles order status, FAQs, bookings, and
lead capture in 30+ languages. Typical deflection rate of 55-70% of tier-1 questions.</p>

<h3>2. AI Lead Generation &amp; Outbound Automation</h3>
<p>An autonomous outbound engine that researches target accounts, drafts personalized
emails grounded in each prospect's context, and books meetings. Includes response
classification and automated follow-up sequences. Built for sales teams that want more
qualified pipeline without adding SDR headcount.</p>

<h3>3. RAG Knowledge Assistants</h3>
<p>Retrieval-augmented assistants over a client's internal documents (policies, product
docs, contracts) or public-facing content. Deployed as internal Slack/Teams copilots or
customer-facing help agents. Answers are grounded in the client's own sources with
citations — no invented facts.</p>

<h3>4. Voice AI &amp; Call Deflection</h3>
<p>Inbound and outbound voice agents for appointment reminders, order updates, and
first-line support. Integrates with existing telephony (Twilio, Vonage). Reduces call
center load during peak periods.</p>

<h3>5. Custom LLM Workflow Automation</h3>
<p>Bespoke automation for document processing, data extraction, and internal workflows —
e.g. invoice parsing, claim triage, and CRM data enrichment. Scoped per engagement.</p>

<h2>Target industries &amp; ideal customers</h2>
<p>We focus on customer-heavy, mid-market businesses where conversation volume and manual
follow-up are real bottlenecks. Strongest fit industries:</p>
<ul>
<li><b>E-commerce &amp; D2C retail</b> — high inbound support and order-status volume.</li>
<li><b>Logistics &amp; last-mile delivery</b> — tracking, exceptions, driver coordination.</li>
<li><b>Real estate &amp; property management</b> — lead qualification, viewing scheduling.</li>
<li><b>Healthcare clinics &amp; dental groups</b> — appointment booking and reminders.</li>
<li><b>Financial services &amp; fintech</b> — onboarding support and document collection.</li>
<li><b>B2B SaaS</b> — outbound pipeline generation and support deflection.</li>
</ul>
<p>Ideal customer size is 20 to 500 employees, typically $5M-$150M in revenue, with an
existing support or sales team feeling the strain of manual volume. We are usually a poor
fit for pre-revenue startups and for enterprises requiring fully on-premise deployment.</p>

<h2>Case studies</h2>
<h3>Meridian Threads (D2C fashion, ~120 staff)</h3>
<p>Deployed the WhatsApp AI Chatbot across support and pre-sales. Automated 63% of tier-1
inquiries, cut median first-response time from 5 hours to under 2 minutes, and recovered an
estimated $410K in abandoned-cart revenue in the first two quarters.</p>

<h3>Cartwright Logistics (regional 3PL, ~300 staff)</h3>
<p>Voice AI plus WhatsApp automation for shipment tracking and delivery-exception handling.
Reduced inbound call volume 41% and freed 9 full-time agents for higher-value work.</p>

<h3>Northlake Dental Group (12-clinic dental group)</h3>
<p>RAG knowledge assistant and appointment booking bot. Reduced no-shows 22% via automated
reminders and answered 80% of routine patient questions without staff involvement.</p>

<h2>Pricing &amp; packages</h2>
<table>
<tr><th>Package</th><th>Monthly</th><th>Includes</th></tr>
<tr><td><b>Starter</b></td><td>$1,500/mo</td>
<td>One channel (WhatsApp or web chat), up to 3,000 conversations/mo, standard
integrations, email support. Cloud-only.</td></tr>
<tr><td><b>Growth</b></td><td>$4,500/mo</td>
<td>Up to 3 channels, 15,000 conversations/mo, CRM + helpdesk integrations, custom RAG
knowledge base, dedicated success manager.</td></tr>
<tr><td><b>Enterprise</b></td><td>Custom</td>
<td>Unlimited channels, custom volume, SSO, data-residency options, SLA-backed uptime,
solutions-engineering retainer.</td></tr>
</table>
<p>All packages require a minimum 3-month initial term. Setup fee ranges from $2,000
(Starter) to $15,000+ (Enterprise) depending on integration complexity. Annual prepay
receives a 15% discount.</p>

<h2>Technologies &amp; integrations</h2>
<p>Models: Groq (Llama 3.x), OpenAI GPT-4 class, and Google Gemini, selected per use case.
Retrieval built on Chroma and pgvector. We integrate with:</p>
<ul>
<li>Messaging: WhatsApp Business API, Instagram, Facebook Messenger, web chat, Twilio SMS.</li>
<li>CRM: Salesforce, HubSpot, Pipedrive.</li>
<li>Helpdesk: Zendesk, Intercom, Freshdesk.</li>
<li>Commerce: Shopify, WooCommerce, Magento.</li>
<li>Telephony: Twilio Voice, Vonage.</li>
<li>Calendars: Google Calendar, Microsoft 365.</li>
</ul>

<h2>Business limitations &amp; conditions</h2>
<ul>
<li>No fully on-premise deployment; Enterprise offers regional data residency only.</li>
<li>Starter tier excludes custom integrations and PHI/regulated-data workloads.</li>
<li>Healthcare deployments require the Growth tier or above (BAA available on Enterprise).</li>
<li>Minimum contract term is 3 months; conversations beyond plan limits are billed per 1,000.</li>
<li>We do not sell standalone model API access or one-off prompt engineering.</li>
<li>Supported languages: 30+ for chat, 12 for voice.</li>
</ul>
"""


def build(out_path: Path = OUT_PATH) -> Path:
    import pymupdf  # PyMuPDF

    out_path.parent.mkdir(parents=True, exist_ok=True)
    story = pymupdf.Story(html=HTML, user_css=CSS)
    writer = pymupdf.DocumentWriter(str(out_path))
    media = pymupdf.paper_rect("a4")
    area = media + (56, 56, -56, -56)  # ~20mm margins
    more = 1
    pages = 0
    while more:
        device = writer.begin_page(media)
        more, _ = story.place(area)
        story.draw(device)
        writer.end_page()
        pages += 1
    writer.close()
    return out_path


if __name__ == "__main__":
    path = build()
    print(f"Wrote {path} ({path.stat().st_size:,} bytes)")
