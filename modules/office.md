# Office

## Purpose

The daily knowledge-work module — everything a founder, consultant, or PM does between strategy and execution. Covers pitching to clients and investors, turning those decks into polished documents, preparing for and capturing meetings, handling client communications, getting quick legal orientation, and structured thinking when you're not sure where to start. You reach for it every time work needs to leave your head and become something someone else will read, sign, or act on. (Formerly named `productivity`; visual design and design extraction moved to the [studio module](./studio.md).)

---

## Components

### Pitching

#### `/rbtv-pitcher` (Roelof / Leo)

- **What**: One entry point for both pitch types. The command asks who the pitch is for — investors or a client — and loads the matching stress-test persona. **Roelof** (investor) is a seasoned VC partner who has reviewed 3,000+ pitches and challenges every claim with "would I write a check based on this?" — calibrated for fund mechanics, unit economics, defensibility, and partner-meeting scrutiny. **Leo** (client) is a veteran enterprise buyer with 20 years in procurement who challenges every slide with "would I sign a contract based on this?" — calibrated for ROI proof, switching costs, and CFO review. Both build the pitch narrative-first across 6 steps — story, data layer, research prompts, slide structure — and never touch HTML.
- **When to use**: You're pitching VCs/angels/accelerators, or a client/prospect/procurement committee, and need a narrative that survives the room after you leave it.
- **How to invoke**: `/rbtv-pitcher` — answer investor or client (skipped when context already says it), then `N` for a new pitch or `E` to revise an existing narrative.
- **What it produces**: `artifacts/pitch-narrative.md` (stress-tested story), `artifacts/pitch-research-prompt.md` (external research prompts), `artifacts/pitch-structure.md` (slide spec — the design handoff contract). HTML deck, image prompts, and PDF are produced downstream by the studio module.
- **Example**: `/rbtv-pitcher` → "investors" → `N` → Roelof immediately challenges market sizing: "Show me the smallest market where you win, then explain the expansion."

> Pitchers are narrative-only. HTML deck design, image prompts, deck editing, and PDF export all execute in the [studio module](./studio.md)'s deck-design workflow via Vivian (`rbtv-designing`) — the pitchers hand off through the `pitch-narrative.md` + `pitch-structure.md` artifacts.

---

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

### Thinking Partners

#### `/rbtv-domcobb`

- **What**: Dom Cobb is a Problem Architect — a former McKinsey consultant obsessed with converting vague needs into structured solutions using MECE, Pyramid Principle, and Problem Trees. Offers a menu: full Problem Structuring (`PS`), a quick PS Lite (`PL`) for simple problems, Idea Sparring (`IS`) — an adversarial idea→MVP stress-test in five moves: break the idea, research to eliminate, shrink to the atomic unit, grumpy-architect review, green-light gate — and three structured-thinking exercises: Pre-Mortem (`PM`), assume a committed project has already failed and work back to failure modes, causes, and mitigations; First-Principles Audit (`FP`), surface and classify assumptions, rewrite them as testable questions, and rebuild from what survives; and Six Thinking Hats (`6H`), walk a topic through De Bono's six perspectives in fixed order with a cross-hat summary.
- **When to use**: When you want a structured problem deliverable — a `structured-problem.md` — that can be handed off or used in client work; quick conversational structuring via `PL` when you're not sure where to start; or `IS` when you have a raw product idea and want it broken, shrunk, and architect-reviewed BEFORE committing to build — the sparring ends in a BUILD verdict with a light MVP brief, or a KILL with recorded cause (a kill is a success: it saves the weeks the idea would have burned). Reach for `PM` when a project is already committed and you want to harden it against the ways it could fail; `FP` when a belief or plan rests on assumptions you want stress-tested from the ground up; `6H` when you want a single topic viewed from every angle — creativity, gut, upside, risk, and facts — before deciding.
- **How to invoke**: `/rbtv-domcobb` (command). Menu appears. Type `PS`, `PL`, `IS`, `PM`, `FP`, or `6H`.
- **What it produces**: A structured problem document (`structured-problem.md`) or an idea-sparring memo (`idea-sparring-{idea}-{date}.md`) carrying a BUILD/KILL verdict.
- **Example**: `/rbtv-domcobb` → `PS` → "I'm not sure why our trial-to-paid conversion is dropping" → Cobb builds a MECE problem tree, structures the drivers via Pyramid Principle, and delivers a `structured-problem.md`. Or → `IS` → "app that does something with my screenshots" → Cobb captures the dump verbatim, breaks the assumptions, maps the graveyard, shrinks it to a reminder-engine atomic unit, and green-lights (or kills) it.

---

## How They Fit Together

The module has three natural flows:

**Pitch flow:** Start with `/rbtv-design-extractor` (studio module) to capture a reference site's visual system → `/rbtv-pitcher` to build the narrative (Roelof or Leo stress-test every slide through step 6) → the narrative + structure artifacts hand off to `rbtv-designing` (Vivian, studio module) for HTML generation, image prompts, deck editing, and PDF export → `rbtv-doc-export` if you need a companion DOCX (proposal, contract, appendix).

**Meeting flow:** `rbtv-meeting-prep` the day before → attend the meeting → paste the transcript into `rbtv-meeting-summarizer` immediately after → use `rbtv-client-email` to send the follow-up the same day.

**Thinking-to-artifact flow:** When the problem is unclear, start with `/rbtv-domcobb` — `PL` for quick conversational structuring, escalating to `PS` when complexity warrants → once the artifact is clear, pass it to a pitcher, the lawyer, or doc-export depending on what it becomes. When the input is a raw product idea rather than a problem, `IS` spars it to a verdict — green-lit ideas hand off to `/rbtv-innovator` M1-M2 or `/rbtv-product-discoverer` (innovation module), or to a product-lifecycle plugin for a full PRD.
