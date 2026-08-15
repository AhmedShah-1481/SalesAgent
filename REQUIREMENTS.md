# AgentHack — Autonomous AI Sales Agent — Requirements

Source: AgentHack_Autonomous_AI_Sales_Agent_Challenge.pdf
This is the authoritative functional spec. Cross-check the build against this file before final submission.

## Core Flow
```
Company PDF/Text -> RAG -> ICP -> Lead Discovery -> Cheap Filtering -> Deep Research
-> Qualification -> Lead Score -> Decision Makers -> Service Matching
-> Personalized Email -> Response Classification -> Follow-Up
-> Meeting Scheduling -> Memory -> Sales Pipeline
```

## 1. Company Knowledge (RAG)
- Input: uploaded company PDF OR pasted text description.
- Must extract and index: what the company sells, services/capabilities, target
  industries/customers, case studies, pricing/packages (if available),
  technologies/integrations, business limitations/conditions.
- This knowledge must ground every downstream decision (service matching,
  personalization). No inventing facts.

## 2. ICP (Ideal Customer Profile)
Ask the user for, before lead generation starts:
- Target location
- Target industry / market
- Company size or other qualification criteria
- Special targeting (specific problem, use case, service, customer type)
Convert into a structured ICP object used throughout the pipeline.

## 3. Lead Discovery (staged, not brute-force)
```
Search -> Cheap Filtering -> Potential Leads -> Deep Research -> Qualification
```
Cheap filtering must eliminate obviously irrelevant companies BEFORE expensive
deep research runs on them.

## 4. Deep Company Research
For promising companies, gather:
- Company profile & website
- Employees / key departments
- News & recent events
- Funding & growth signals
- Technology / tools / integrations in use
- Possible business problems / buying signals
- Other qualification evidence

## 5. Lead Qualification & Confidence Score
- Every researched company gets a confidence score + written explanation.
  Example: "ABC Logistics — 92% Potential Lead"
- Explanation should reference: ICP fit, problem fit, service fit, buying
  signals, company size, location, evidence quality.
- System MUST be able to output "Not Qualified" — goal is best leads, not max
  contacts.

## 6. Service Matching
- Determine which of the company's own products/services best fits each
  qualified prospect.
- Must be grounded in the RAG knowledge base, not invented.
- Example: high WhatsApp inquiry volume -> recommend WhatsApp AI chatbot over
  other services.

## 7. Decision-Maker Identification
- Identify relevant people per qualified company: CEO/Founder/Co-Founder, CTO,
  CFO, COO, VP Sales/Head of Sales, Head of Support, or other role relevant to
  the recommended service.
- Prioritize people most relevant to the specific service being sold.

## 8. Personalized Outreach
- Generate a personalized email per selected contact.
- Consider: their role, company situation, likely problem, matching service.
- Evidence-based only — do not invent facts about the prospect.
- Role-specific framing (e.g. CTO email emphasizes integrations/technical fit;
  sales leader email emphasizes productivity/revenue impact).

## 9. Email + Meeting Link
- Send outreach email via real or simulated email mechanism.
- Include a meeting/booking link when appropriate.
- Log every outreach action with: company, contact, role, lead score,
  recommended service, message content, evidence, timestamp.

## 10. Response Classification
Classify inbound replies into (at least):
Positive/Interested, Meeting requested, Question, Pricing objection,
Technical objection, Not interested, Not now, Wrong person/Referral, Other.
Classification determines the pipeline's next action.

## 11. Follow-Up
- No response -> auto follow-up.
  `Day 0 -> Email #1 -> Wait 3 days -> Follow-up Agent -> Email #2`
- On positive reply + meeting finalized -> reply with meeting link + fixed time.

## 12. Meeting & Admin Automation
- Generate/provide meeting link with fixed finalized time.
- Send meeting details to admin via WhatsApp when meeting is finalized.
- Store meeting info in memory.
- Remind admin 30 minutes before meeting.
- Reminder must include a short briefing: customer problem, recommended
  service, key objections/questions, discussion points.

## 13. Memory
- **Short-term**: current research, current conversation, current task,
  current meeting context, active agent state.
- **Long-term**: company history, contacts, emails, replies, objections, lead
  scores, follow-ups, meetings, final sales status.

## 14. Sales Pipeline (visual state)
```
Discovered -> Potential -> Researching -> Qualified -> Contacted -> Interested
-> Meeting Scheduled -> Converted
```
Plus negative states: Not Qualified, Not Interested, Do Not Contact.

## Required Features Checklist (Section 17)
- [ ] Company knowledge: PDF or text input, RAG-based understanding
- [ ] ICP: location, industry, company criteria, special targeting
- [ ] Lead discovery: search, cheap filtering, potential leads
- [ ] Deep research: company, people, news, funding, technology, signals
- [ ] Qualification: lead confidence % + explanation
- [ ] Decision makers: relevant people + contact details when available
- [ ] Sales: role-specific personalized email
- [ ] Responses: classification + next action
- [ ] Follow-up: 3-day follow-up + second email
- [ ] Meetings: fixed time + meeting link
- [ ] Memory: short-term + long-term
- [ ] Pipeline: persist and update lead state through full lifecycle

## Extra Credit (Section 18)
- New meeting link generated when sending the email.
- WhatsApp integration: message the company's WhatsApp number if available.
- Admin reminder also sent via WhatsApp with meeting link.

## Evaluation Weighting
- Required features working perfectly: 70%
- Extra features: 15%
- Frontend: 15%
- Overall: Video Presentation 60% / Code 40%

## Submission Requirements
1. Live Demo Video — max 1.5 minutes, working end-to-end workflow.
2. Code Explanation Video — max 1 minute, architecture/agents/RAG/memory/tools.
3. GitHub Repo — must include `.env.example`.
