# Office

## Purpose

The daily knowledge-work module — everything a founder, consultant, or PM does between strategy and execution. Covers turning narratives into polished documents, preparing for and capturing meetings, handling client communications, and getting quick legal orientation. You reach for it every time work needs to leave your head and become something someone else will read, sign, or act on. (Formerly named `productivity`; visual design, design extraction, narrative strategy, and the studio loop entry — `/rbtv-strategist` — moved to the [studio module](./studio.md). The structured-thinking persona `/rbtv-domcobb` was retired 2026-08-21 — it lives on as the `brainstorm` function, Dom Cobb, in the mirror-format `core/functions` component.)

---

## Components

### Documents

#### `rbtv-doc-export`

- **What**: Converts a markdown or HTML file into a branded PDF or legal-styled DOCX. Detects document type automatically — legal documents (contracts, NDAs, agreements) get clean legal styling; everything else gets your workspace's brand colors, logo, and typography. Handles config generation if brand artifacts don't exist yet.
- **When to use**: You have a finished document — proposal, contract, report, agreement — and need a client-ready file. Also use it first-time on a project to generate the three brand config artifacts (`document-style.yaml`, `document-style.css`, `document-config.js`).
- **How to invoke**: `rbtv-doc-export` (skill). Provide a file path. It asks PDF or DOCX, then handles the rest. For brand setup, invoke the skill without a file path.
- **What it produces**: `.pdf` or `.docx` in the same directory as the input file, using workspace branding or legal styling.
- **Example**: "Export this proposal to PDF" → `rbtv-doc-export` reads your brand folder, finds the config artifacts, runs `md-to-pdf`, and drops `proposal.pdf` next to your markdown.

---

### Client Engagement

#### `rbtv-client-email`

- **What**: Drafts external emails to clients, prospects, or partners. Enforces specific voice principles: compaction (no filler), co-construction over prescription (proposes options, not mandates), plain-text-friendly formatting, and soft commitments with concrete parameters. Four-step workflow — context discovery, voice loading, strategic check, draft + compact.
- **When to use**: Any email that leaves your organization: proposals, follow-ups, status updates, security responses, pricing conversations. Especially valuable when stakes are high or tone is tricky.
- **How to invoke**: `rbtv-client-email` (skill). Describe the email you need, or paste a draft for refinement.
- **What it produces**: A ready-to-send email draft, compacted to remove filler and checked against communication principles.
- **Example**: "Follow up with Acme after the demo — they went quiet for two weeks" → skill gathers context, checks strategic angle, drafts a concise message that proposes a next step without pressuring.

---

#### `/rbtv-lawyer`

- **What**: A portable corporate legal advisor agent. Covers INPI trademarks, LTDA/SA corporate law, IP assignment, employment formalization, and corporate transactions. Reads your company's legal folder for context, detects jurisdiction (Brazilian CNPJ → Portuguese law; EIN → US law), loads only the relevant reference files, and cites articles and legislation specifically. Produces formal legal documents (contracts, agreements) and recommends professional counsel for litigation or high-value transactions.
- **When to use**: You need legal orientation on a corporate matter — trademark filing, contract drafting, understanding an employment structure, reviewing an IP clause. Not a substitute for a licensed lawyer on high-stakes matters, but the right first step before hiring one.
- **How to invoke**: `/rbtv-lawyer` (command). Name the company and describe the task.
- **What it produces**: Legal analysis with specific citations, or a formal document draft (markdown, optionally exported to DOCX via `rbtv-doc-export`).
- **Example**: `/rbtv-lawyer` → "Draft an IP assignment clause for Tecer's new contractor agreement" → agent reads Tecer's legal folder, detects Brazilian jurisdiction, loads `contratos-pi-cessao.md`, drafts clause in Portuguese with cited articles.

---

### Meetings

#### `rbtv-meeting-prep`

- **What**: A guided meeting preparation workflow that produces a strategic cheat sheet. Classifies the meeting type, runs discovery with you (never generates content without your input), and builds the cheat sheet incrementally. Offers web search for unknowns during prep. Never skips or optimizes the step sequence — the structure IS the preparation.
- **When to use**: Before any meeting where stakes justify 15-30 minutes of structured prep: client QBR, investor update, important internal sync, sales call. The discipline of the workflow forces you to articulate what you actually want from the meeting.
- **How to invoke**: `rbtv-meeting-prep` (skill). Describe the meeting (who, when, what it's about).
- **What it produces**: A strategic cheat sheet — talking points, anticipated objections, your goals for the meeting, background on participants.
- **Example**: `rbtv-meeting-prep` → "Investor update with Sequoia next Thursday" → workflow classifies as investor meeting, asks about relationship history, surfaces 3 risks to address, builds cheat sheet.

---

#### `rbtv-meeting-summarizer`

- **What**: Processes meeting transcripts into structured summaries using type-specific prompts. Classifies the meeting (client, investor, internal, product interview, general), loads your workspace glossary for transcription correction, routes the summary to the right folder, and applies a specialized analysis lens per type. Client meetings get signal capture and commercial terms extraction; investor meetings get performance coaching and founder signals; product interviews get hypothesis validation synthesis.
- **When to use**: After any meeting where you have a transcript. Paste the transcript path or content and the skill handles classification, routing, and analysis.
- **How to invoke**: `rbtv-meeting-summarizer` (skill). Point to a transcript file or paste content. Or say "summarize this meeting."
- **What it produces**: A structured summary saved to the correct project/meeting folder, with type-adapted analysis sections.
- **Example**: `rbtv-meeting-summarizer` → @mention `meetings/2026-05-01-demo-acme.md` → classified as client meeting, glossary applied, summary produced with opportunity signals and next-step flags.

---

## How They Fit Together

The module's natural flow:

**Meeting flow:** `rbtv-meeting-prep` the day before → attend the meeting → paste the transcript into `rbtv-meeting-summarizer` immediately after → use `rbtv-client-email` to send the follow-up the same day.
