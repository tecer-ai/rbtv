# Productivity

## Purpose

The largest RBTV module — everything a founder, consultant, or PM does between strategy and execution. Covers pitching to clients and investors, turning those decks into polished documents, preparing for and capturing meetings, handling client communications, getting quick legal orientation, and structured thinking when you're not sure where to start. Think of it as the daily knowledge-work toolkit: you reach for it every time work needs to leave your head and become something someone else will read, sign, or act on.

---

## Components

### Pitching

#### `/rbtv-client-pitcher` (Leo)

- **What**: Leo is a veteran enterprise buyer with 20 years in procurement and consulting. She sits on the buyer's side of the table and stress-tests every slide against the question "would I sign a contract based on this?" She builds client/sales pitch decks narrative-first — story is agreed and challenged before any HTML is generated. Produces a full deck (narrative, HTML, AI image prompts, PDF) across 10 steps.
- **When to use**: You're pitching a product, service, or proposal to a client, prospect, or procurement committee. You need the deck to survive a CFO review, not just a founder's enthusiasm check.
- **How to invoke**: `/rbtv-client-pitcher` — then type `N` for a new pitch or `E` to refine an existing one.
- **What it produces**: Narrative document, branded HTML deck, AI image prompts, synthesis memo, PDF export.
- **Example**: `/rbtv-client-pitcher` → `N` → @mention `project-memo.md` → Leo reads existing docs, then starts drilling: "Why would this buyer switch from what they're doing today?"

---

#### `/rbtv-investor-pitcher` (Roelof)

- **What**: Roelof is a seasoned VC partner who has reviewed 3,000+ pitches and made 40 investments. He stress-tests every claim from the investor's side — "would I write a check based on this?" Same workflow architecture as the client pitcher but calibrated for fund mechanics, unit economics, defensibility, and partner-meeting scrutiny.
- **When to use**: You're raising from VCs, angels, or accelerators and need a deck that survives the room after you leave it.
- **How to invoke**: `/rbtv-investor-pitcher` — then type `N` for a new pitch or `E` to edit an existing one.
- **What it produces**: Same artifact set as the client pitcher — narrative, HTML deck, image prompts, synthesis memo, PDF — framed for investor diligence.
- **Example**: `/rbtv-investor-pitcher` → `N` → Roelof immediately challenges market sizing: "Show me the smallest market where you win, then explain the expansion."

---

#### `rbtv-designing` (Vivian)

- **What**: Vivian is the visual layer for both pitch flows — a Creative Director who translates strategy into HTML deck design, AI image prompts, and brand visual identity. She always offers three visual directions and names which one she believes in. Design is explicitly downstream of narrative: she takes completed narrative docs as input and never redoes strategic work.
- **When to use**: After narrative is locked and you're ready to generate the HTML deck, produce AI image prompts, export to PDF, or design brand visual guidelines. The pitchers hand off to Vivian automatically at step 7 — you can also invoke her standalone for any of those tasks.
- **How to invoke**: `rbtv-designing` (skill, not a slash command). Menu options: `PD` (full deck design + export), `PI` (image prompts only), `PDF` (PDF export + QA), `BV` (brand visual identity).
- **What it produces**: Branded HTML deck, a set of AI image prompts ready to paste into Midjourney/DALL-E, PDF via Decktape, visual brand guidelines.
- **Example**: After Leo finishes the narrative, she hands off: "Calling Vivian." Vivian opens: "I'm seeing a steel-and-gold palette — quiet authority. Here are three directions."

---

### Documents

#### `rbtv-doc-export`

- **What**: Converts any markdown file into a branded PDF or legal-styled DOCX. Detects document type automatically — legal documents (contracts, NDAs, agreements) get clean legal styling; everything else gets your workspace's brand colors, logo, and typography. Handles config generation if brand artifacts don't exist yet.
- **When to use**: You have a finished markdown document — proposal, contract, report, agreement — and need a client-ready file. Also use it first-time on a project to generate the three brand config artifacts (`document-style.yaml`, `document-style.css`, `document-config.js`).
- **How to invoke**: `rbtv-doc-export` (skill). Provide a markdown file path. It asks PDF or DOCX, then handles the rest. For brand setup, invoke the skill without a file path.
- **What it produces**: `.pdf` or `.docx` in the same directory as the input file, using workspace branding or legal styling.
- **Example**: "Export this proposal to PDF" → `rbtv-doc-export` reads your brand folder, finds the config artifacts, runs `md-to-pdf`, and drops `proposal.pdf` next to your markdown.

---

#### `/rbtv-design-extractor`

- **What**: Navigates a live website, captures multiple pages via screenshot + DOM/CSS extraction, and produces structured design token documentation — colors, typography, spacing, layout, CSS variables. Outputs a design brief and/or `design-tokens.json`.
- **When to use**: You want to clone, adapt, or analyze a competitor's or reference site's visual system before starting a design project. Feeds directly into Vivian's brand work.
- **How to invoke**: `/rbtv-design-extractor` (command). Provide a URL. The workflow maps the site, confirms the capture list with you, then extracts.
- **What it produces**: Design brief (markdown) and/or `design-tokens.json` with every token sourced to `"dom"` or `"screenshot-sampled"`.
- **Example**: `/rbtv-design-extractor` → `https://competitor.com` → workflow captures 6 pages, extracts 47 tokens, outputs `design-brief.md` and `design-tokens.json`.

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

#### `/rbtv-operator`

- **What**: A thinking partner for complex or unclear tasks. Opens with a discovery drill — asks clarifying questions until it understands the problem at 95% confidence — then deploys a move set: probe, map (reads workspace files), structure (runs MECE/Pyramid), propose (2-3 paths with tradeoffs), challenge (stress-tests your framing), draft (writes the artifact), or handoff (generates a prompt for the next agent). No sycophancy, no rubber-stamping.
- **When to use**: You're stuck, unclear, or facing a decision with too many variables. Not for tasks with a known shape (use the specific skill for those). Best for "I need to think through this before I can even say what I need."
- **How to invoke**: `/rbtv-operator` (command). You can start with a topic or just invoke it cold — it will ask "What problem are we solving today?"
- **What it produces**: No fixed output artifact. The session IS the output — clarified problem, structured options, or a ready-to-use prompt/artifact depending on where the drill leads.
- **Example**: `/rbtv-operator` → "I'm not sure whether to pitch Tecer as a finance tool or a compliance tool" → operator runs discovery, maps workspace docs, challenges both framings, proposes positioning options with tradeoffs.

---

#### `/rbtv-domcobb`

- **What**: Dom Cobb is a Problem Architect — a former McKinsey consultant obsessed with converting vague needs into structured solutions using MECE, Pyramid Principle, and Problem Trees. Offers a menu: full Problem Structuring (`PS`), a quick PS Lite (`PL`) for simple problems, Prompting Assistance (`PR`) for crafting effective AI prompts, AI Web Project creation (`AWP`) for ChatGPT/Claude/Gemini/Manus assistants, and Add Knowledge (`AK`) for documenting new AI models or prompting techniques.
- **When to use**: When you want a structured problem deliverable — a `structured-problem.md` — that can be handed off, used in client work, or fed to another AI consulting workflow. More deliberate than Operator; Operator borrows these frameworks in passing, Cobb makes the structured artifact the goal.
- **How to invoke**: `/rbtv-domcobb` (command). Menu appears. Type `PS`, `PL`, `PR`, `AWP`, or `AK`.
- **What it produces**: Depending on menu selection: structured problem document, prompting analysis, or a complete AI assistant project brief (system prompt, knowledge base structure, behavior guidelines).
- **Example**: `/rbtv-domcobb` → `PR` → "Help me craft a prompt for extracting action items from client emails" → Cobb applies prompting technique knowledge, asks clarifying questions, delivers a tested prompt structure.

---

## How They Fit Together

The module has three natural flows:

**Pitch flow:** Start with `/rbtv-design-extractor` to capture a reference site's visual system → `/rbtv-client-pitcher` or `/rbtv-investor-pitcher` to build the narrative (Leo or Roelof stress-test every slide) → `rbtv-designing` (Vivian) takes over at step 7 for HTML generation, image prompts, and PDF export → `rbtv-doc-export` if you need a companion DOCX (proposal, contract, appendix).

**Meeting flow:** `rbtv-meeting-prep` the day before → attend the meeting → paste the transcript into `rbtv-meeting-summarizer` immediately after → use `rbtv-client-email` to send the follow-up the same day.

**Thinking-to-artifact flow:** When the problem is unclear, start with `/rbtv-operator` (discovery + move set, no fixed output) → if a structured problem deliverable is the goal, escalate or switch to `/rbtv-domcobb` → once the artifact is clear, pass it to a pitcher, the lawyer, or doc-export depending on what it becomes.
