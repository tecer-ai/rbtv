---
projectName: 'robotville-v4.0'
currentMilestone: 'M1: Conception'
currentFramework: 'Lean Canvas'
stepsCompleted: ['bi-m1-working-backwards', 'bi-m1-jobs-to-be-done', 'bi-m1-problem-solution-fit', 'bi-m1-lean-canvas']
lastUpdated: '2026-02-13'
---

# Robotville v4.0 Project Memo

---

## For AI Agents

**Template reference:** This document was created from `_bmad/rbtv/workflows/bi-business-innovation/templates/project-memo.md`.

**Workflow reference:** Read the bi-business-innovation workflow for milestone structure and framework sequence.

**Output location:** All outputs saved to `_bmad-output/robotville-v4.0/founder/`.

---

## Execution Context

> **CRITICAL FOR ALL AGENTS:** This project has a **2-day delivery target** (set 2026-02-13). The founder has explicitly requested maximum speed. This is a **delivery/access layer** for an existing system (BMAD + RBTV), NOT new business logic. The product definition is1 already clear. Business Innovation frameworks should be completed quickly — the core intellectual work (what the product is, who it's for, why it wins) is already known. Focus on documenting decisions, not discovering them.
>
> **VC context:** Founders have a meeting with top Brazilian VCs in ~2 weeks. This prototype IS the demo. The founders have been building RBTV as an internal tool for months and want to show it as proof of AI competence + potential product.

---

## Introduction

Robotville v4.0 makes BMAD + RBTV accessible through a messaging interface (Slack, Discord, or similar) instead of requiring the Cursor IDE. A VPS runs a local BMAD instance with RBTV installed; an AI runtime (OpenClaw or Nanobot) connects to an AI provider and follows the same RBTV workflows. Users command the agent through chat — same workflows, same quality, no IDE required.

Origin: Over months of building RBTV as an internal tool for business innovation, the founders realized the system itself is the most developed project they have. Making it accessible outside Cursor turns an internal tool into a demonstrable product.

Target customer: Initially the two founders. Then non-technical founders who want structured AI-guided business innovation without needing a code editor.

---

## Problem

RBTV provides 22+ innovation frameworks across 6 milestones, from idea to deployed website. But it only runs inside Cursor — an IDE designed for developers. Non-technical founders (the primary audience for business innovation tooling) can't use it. Even technical users are locked to their desktop. The business innovation workflows are platform-agnostic in design but platform-dependent in delivery.

---

## Solution

Add a messaging-based delivery layer to RBTV. The AI agent runs on a VPS with a full BMAD+RBTV installation. A new `_mobile/` folder inside `_bmad/rbtv/` contains the adapter layer: bootstrap instructions, command routing (mapping chat `/commands` to RBTV workflows), aggregated `skills.md` and `rules.md` files (auto-updated from `.cursor/` YAML headers), and deployment configs. Optionally includes a Python install script for setup automation.

Key architectural decision: **one codebase, two delivery channels.** The messaging layer is a feature of RBTV, not a fork. All business logic stays in the existing workflow files.

After completing all 6 milestones, the bot deploys: project website to `robotville.ai/app/{project-name}`, presentation (from project-memo) to `robotville.ai/docs/{project-name}`.

**Stack decision (2026-02-13):** Nanobot + Slack (see Technical Research section in Appendix for full rationale).

**Remaining stack decisions:**
- VPS provider: TBD
- AI provider: TBD (Nanobot supports OpenRouter, Anthropic, OpenAI, DeepSeek, etc.)
- Domain: robotville.ai (owned)

---

## Tenets

**One Codebase, Two Channels**
The messaging delivery layer is a feature of RBTV, not a separate product. No forking, no mirroring. `_mobile/` lives inside `_bmad/rbtv/` and reads the same workflows. If it can't be maintained as part of RBTV, it shouldn't exist.

**Integration Simplicity Over Feature Richness**
Choose the messaging platform and AI runtime that require the least integration work. Two days to prototype means every hour of setup complexity is a direct threat.

**The Workflows Are the Product**
The value is in the 22 frameworks and 6-milestone pipeline, not in the chat interface. The delivery layer is infrastructure. Never let infrastructure decisions slow down or compromise the workflow experience.

---

## Progress

### M1 Conception

[In progress — Working Backwards + Jobs-to-be-Done + Problem-Solution Fit + Lean Canvas complete. 4/6 frameworks done.]

**Completed Frameworks:**
- Working Backwards — **Completed** — [m1-conception/working-backwards.md](m1-conception/working-backwards.md)
  - Primary Customer: Aspiring first-time business creators (25-50), domain expertise, no startup experience, limited tech sophistication
  - Core Problem: Business innovation methodology locked behind expensive consultants, MBAs, or technically demanding tools
  - Decision: Yes — with caveats (user completion, multi-tenant isolation, willingness to pay need M2 validation)
  - Top Assumptions: (1) Users complete multi-step frameworks via chat, (2) Per-user isolation feasible, (3) Willingness to pay $15-50/mo
- Jobs to Be Done — **Completed** — [m1-conception/jobs-to-be-done.md](m1-conception/jobs-to-be-done.md)
  - Primary Job: Methodology Gap — "When I decide to pursue a business idea but don't have startup experience or know what steps to take, I want structured step-by-step guidance through the thinking before building, so I can go from raw idea to validated concept"
  - Key Forces: Push (methodology inaccessible), Pull (chat-based + end-to-end), Anxiety (AI gimmick fear), Habit (doing nothing)
  - Top Assumptions: (1) Users recognize thinking-before-building gap, (2) Chat sufficient for complex frameworks, (3) AI pushback perceived as valuable not threatening
- Problem-Solution Fit — **Completed** — [m1-conception/problem-solution-fit.md](m1-conception/problem-solution-fit.md)
  - Segment: Aspiring first-time business creators at the moment they cross from daydreaming to active intent
  - Problem-Solution Thesis: Social validation loop replaced by progress loop — AI mentor via messaging produces structured artefacts, not just good feelings
  - Core Mechanism: Conversational framework methodology + end-to-end thinking→building pipeline (M1-M6) for digital businesses
  - Party Mode Insights: (1) Inaction is a competing product with real benefits, not just a default, (2) Emotions are curiosity+uncertainty not imposter syndrome, (3) Desired outcome is clarity+permission to act not rigorous analysis
  - Top Assumptions: (1) PSF-1: Meaningful % cross from daydream to intent, (2) PSF-2: First interaction beats social validation loop, (3) PSF-3: Users complete multi-step frameworks via chat
- Lean Canvas — **Completed** — [m1-conception/lean-canvas.md](m1-conception/lean-canvas.md)
  - Version: v0.1 — Idea Stage (Pre-product)
  - Business Model: ~$10/mo subscription + $30-50 custom domain deployment fee. Free tier at `robotville.ai/app/{project}` doubles as marketing
  - UVP: "YC mentor in your pocket — through a chat message." Structured AI mentor via messaging, 22 frameworks, end-to-end thinking→building pipeline
  - Unfair Advantage: Honest — no moat today. Building toward methodology compound + structured business data + Brazil WhatsApp/Pix distribution
  - Unit Economics: Tight but viable at $10/mo if API costs stay under $5/framework. LTV:CAC ratio 5-16x (hypothesis)
  - 18 assumptions tagged. Top 3 existential: (1) Addressable segment large enough (PSF-1), (2) First interaction beats comfort zone (PSF-2), (3) Users complete multi-step frameworks via chat (PSF-3)
- Competitive Landscape — [Pending] — [Link]
- Five Whys — [Pending] — [Link]

### M2 Validation

[Not started.]

**Completed Frameworks:**
- Leap of Faith — [Pending] — [Link]
- Assumption Mapping — [Pending] — [Link]
- TAM-SAM-SOM — [Pending] — [Link]
- Unit Economics — [Pending] — [Link]
- Technology Readiness Level — [Pending] — [Link]
- Pre-Mortem — [Pending] — [Link]

### M3 Brand

[Not started.]

**Completed Frameworks:**
- Brand Archetypes — [Pending] — [Link]
- Brand Prism — [Pending] — [Link]
- Golden Circle — [Pending] — [Link]
- Brand Positioning — [Pending] — [Link]
- Tone of Voice — [Pending] — [Link]
- Messaging Architecture — [Pending] — [Link]

### M4 Prototypation

[Not started.]

### M5 Market Validation

[Not started.]

### M6 MVP

[Not started.]

---

## Canonical Assumption Inventory

**Consolidated from:** Working Backwards, Jobs-to-be-Done, Problem-Solution Fit. PSF IDs are canonical — all WB and JTBD assumptions mapped to PSF equivalents or listed as new entries.

**M2 guidance:** PSF produced the most rigorous falsification tests with concrete thresholds and measurable pass/fail criteria. When building Leap of Faith and Assumption Mapping in M2, use PSF's test designs as the starting point — not WB or JTBD's softer qualitative framing.

### Existential (if any fails, there is no business)

| ID | Assumption | Category | Confidence | Falsification Test |
|-----|-----------|----------|------------|-------------------|
| PSF-1 | A meaningful % of idea-havers cross from daydreaming to active intent — addressable SAM is "people who've decided to act," not total TAM | Behavioural | Low | Survey 100 people with business ideas; if <5% took concrete action in 6 months, segment is dangerously small |
| PSF-2 | First Robotville interaction delivers more immediate reward than talking to friends who say "great idea!" (beats social validation loop) | Behavioural | Low | Beta: Day 1→Day 2 return rate; if <30%, first interaction loses to comfort zone |
| PSF-3 | Users complete multi-step frameworks via chat — not abandon after first session | Behavioural | Low | Track M1 completion; if <20% finish all 6 M1 frameworks, format is broken |

### High Priority

| ID | Assumption | Category | Confidence | Falsification Test |
|-----|-----------|----------|------------|-------------------|
| PSF-4 | Chat-based delivery sufficient for complex business frameworks (linear, text-heavy, no visual canvas) | Behavioural / Technical | Medium | Compare same framework via Robotville vs human mentor; if >30% quality gap, chat insufficient |
| PSF-5 | AI pushback (critical, zero sycophancy) perceived as valuable, not threatening, by first-time founders | Behavioural | Medium | Beta: track drop-off at first high-friction pushback; if >40% abandon at that moment, calibration wrong |
| PSF-6 | Users who complete thinking (M1-M3) trust same system to build (M4-M6) — end-to-end transition feels natural | Behavioural / Technical | High (founder) | Track M3→M4 conversion; if <50% proceed, transition broken. See Founder Convictions below |
| PSF-7 | Per-user memory and project isolation feasible without Nanobot runtime rebuild | Technical | Medium | Spike: 3 simultaneous sessions, verify complete isolation; any cross-contamination = architecture redesign |
| PSF-8 | Context window consolidation (auto-summarize at 50 msgs) doesn't destroy mid-framework state | Technical | Medium | Run full WB through Nanobot, trigger consolidation mid-framework, compare output quality before/after |
| PSF-9 | Willingness to pay $15-50/month after free beta | Economic | Low | After beta: offer paid tier to M1 completers; if <5% convert at $15/month, pricing wrong |
| PSF-10 | AI API costs per framework session stay below $2-5 | Economic | Medium | Measure actual costs per completed framework; if avg >$20 per M1, model needs restructuring |

### Lower Priority

| ID | Assumption | Category | Confidence | Falsification Test |
|-----|-----------|----------|------------|-------------------|
| WB-11 | Lovable export integration technically feasible | Technical | Medium | Engineering spike |
| WB-12 | Messaging platform policies (Slack, WhatsApp) remain favorable for bot distribution | External | Medium | Monitor platform bot policies quarterly |

### Founder Convictions

**On PSF-6 (end-to-end M1-M6 pipeline):** Founder conviction is high. The target customer doesn't know build tools (Lovable, Cursor, vibe coding) exist, let alone how to operate them. Supporting evidence: only ~20% of monthly ChatGPT users in the US are daily users — and "daily" includes search-mode queries, single prompts, and hallucination-prone sessions. The target audience's AI sophistication is near zero. They cannot "leave Robotville after M3 and build elsewhere" because they have no awareness of where "elsewhere" is. Robotville's end-to-end pipeline isn't a feature — it's the only viable path for this segment. This is what RBTV uniquely delivers: the full thinking-to-building pipeline through a single conversational interface. Still listed as assumption for intellectual honesty; pending M2 user validation.

---

## Open Questions

1. **`_mobile/` architecture:** Exact file structure for the adapter layer — bootstrap, command routing, skills/rules aggregation, session management. Preliminary design exists (see Appendix), needs finalization.
2. **Deployment pipeline:** How does the bot push generated sites to `robotville.ai/app/{project-name}`? GitHub Pages? Direct VPS hosting? CDN?
3. **VPS provider selection:** Needs research — requirements are: Docker support, reasonable cost, reliable uptime.
4. **Playwright/MCP gap:** Nanobot has no MCP support. RBTV uses Playwright MCP from M3 onward (brand/prototype). Options: (a) skip browser-dependent workflows in prototype, (b) wrap Playwright CLI calls via shell exec, (c) write a custom Nanobot tool. Decision deferred — not blocking M1-M2.
5. **Context window strategy:** Nanobot auto-consolidates after 50 messages. Need to validate that RBTV's project-memo-based state tracking is sufficient to maintain workflow continuity across consolidation events. Consider increasing `memory_window` to 100+ for richer context.
6. **Onboarding experience design:** The first interaction is existential for the product (see PSF-2). Prototype uses the existing Mentor agent flow as-is — sufficient for demo and initial testing. Before open beta, the onboarding experience must be deliberately designed and validated. Do not skip this.

---

## Next Steps

1. Complete M1 frameworks (rapid pass — decisions are already made, just documenting)
2. Design and implement `_mobile/` folder structure inside `_bmad/rbtv/`
3. Set up VPS + Nanobot + Slack integration
4. Test: run a simple RBTV workflow (e.g., `/bmad-rbtv-help`) through Slack

---

## Appendix

### Reference Files

- **RBTV Vision:** `_bmad/rbtv/_admin/docs/rbtv-vision.md`
- **RBTV README:** `_bmad/rbtv/README.md`
- **RBTV Get Started:** `_bmad/rbtv/get_started.md`
- **Domain:** robotville.ai (owned by founders)
- **Founder background:** IB, VC, corporate development — business-focused, non-technical

### Technical Research: Nanobot Assessment (2026-02-13)

**Decision: Nanobot + Slack selected as runtime + messaging for prototype.**

No need to research OpenClaw — Nanobot covers all requirements for the 2-day target. OpenClaw is 430K+ lines vs. Nanobot's ~4K; the complexity difference alone disqualifies it for a rapid prototype.

#### Nanobot Tool Compatibility with RBTV

| RBTV Need | Nanobot Tool | Status |
|---|---|---|
| Read files | `read_file` | Direct match |
| Write files | `write_file` | Direct match, auto-creates parent dirs |
| Edit files (string replace) | `edit_file` | Direct match — `old_text` → `new_text`, requires uniqueness |
| List directories | `list_dir` | Direct match |
| Shell commands (git, mkdir, etc.) | `exec` | 60s timeout (configurable), safety guards, workspace restriction |
| Web search | `web_search` | Via Brave API |
| Web fetch | `web_fetch` | Fetch and read URLs |
| Sub-agents | `spawn` | Background tasks with file/shell/web tools, isolated context |
| Grep/ripgrep | Via `exec` | No native grep tool; use `exec` to run `rg` or `grep` |

#### Nanobot Context System

- **Bootstrap files** loaded into system prompt on every call: `AGENTS.md`, `SOUL.md`, `USER.md`, `TOOLS.md`, `IDENTITY.md` — placed in workspace root.
- **Skills system:** `workspace/skills/{name}/SKILL.md` — auto-summarized in system prompt. Agent reads full skill via `read_file` on demand. Skills can be marked `always=true` for auto-loading.  This is directly compatible with RBTV's `.cursor/skills/` pattern.
- **Memory:** Two-layer system. `MEMORY.md` (long-term facts, always in system prompt) + `HISTORY.md` (grep-searchable log). Auto-consolidated from conversation.
- **Session persistence:** Per `channel:chat_id`. Survives restarts.
- **Memory window:** Default 50 messages. When exceeded, LLM summarizes old messages → MEMORY.md + HISTORY.md, trims session to last ~10-25 messages.

**Context risk for RBTV:** If a single framework takes 50+ messages, consolidation may lose mid-step context. **Mitigation:** RBTV's `project-memo.md` frontmatter (`currentMilestone`, `currentFramework`, `stepsCompleted`) is external state that persists regardless of context window. Each step file is self-contained. The `_mobile/SOUL.md` bootstrap must include a rule: "Before every response, read `project-memo.md` frontmatter for current state. After every framework completion, update project-memo immediately." Also consider setting `memory_window: 100` in nanobot config for richer retention.

#### Slack Integration

- **Protocol:** Socket Mode (WebSocket) — no public URL or webhook needed.
- **Setup:** Create Slack app → enable Socket Mode → get bot token (`xoxb-...`) + app token (`xapp-...`) → configure `channels.slack` in nanobot config → `nanobot gateway`.
- **Features:** Thread support, DM support, `@mention` policy for channels, `allowFrom` whitelist.
- **Estimated setup time:** 30 minutes.

#### WhatsApp Integration

- **Protocol:** Node.js bridge using `@whiskeysockets/baileys` (WhatsApp Web protocol).
- **Setup:** Requires Node.js >= 18 + QR code scan. Two processes (bridge + gateway).
- **Concerns:** QR re-scan required periodically. More friction than Slack.
- **Verdict:** Works for future, but Slack is cleaner for 2-day prototype. WhatsApp can be added later.

#### Preliminary `_mobile/` Folder Design

```
_bmad/rbtv/_mobile/
├── install.py              # Setup script: copies BMAD mirror, installs RBTV, configures nanobot workspace
├── AGENTS.md               # Bootstrap: agent persona routing (mentor, domcobb, etc.)
├── SOUL.md                 # Bootstrap: RBTV core rules, "always read project-memo before responding"
├── TOOLS.md                # Bootstrap: /command → RBTV workflow file mapping table
├── USER.md                 # Bootstrap: user preferences template
├── skills/                 # Copies/symlinks of RBTV skill files
│   ├── plan/SKILL.md
│   ├── doc/SKILL.md
│   ├── git/SKILL.md
│   └── ...
└── config-template.json    # Nanobot config with Slack channel + provider presets
```

**`install.py` script responsibilities:**
1. Copy BMAD from `_bmad/rbtv/_admin/docs/BMAD-mirror/` to target workspace
2. Move `rbtv/` into `_bmad/rbtv/` in the workspace
3. Run RBTV's standard installer (`_config/install-rbtv.py`)
4. Copy `_mobile/` bootstrap files (`AGENTS.md`, `SOUL.md`, `TOOLS.md`, `USER.md`) into nanobot workspace root
5. Copy/symlink skills into `workspace/skills/`
6. Apply `config-template.json` as base for `~/.nanobot/config.json`

**Key insight from founder:** RBTV already has a BMAD mirror at `_admin/docs/BMAD-mirror/`, so installation can be self-contained — no need to clone BMAD separately. The `install.py` script copies the mirror to the workspace, then moves RBTV to its correct position.

#### Known Gap: No MCP Support

Nanobot does not support MCP (Model Context Protocol). RBTV uses Playwright MCP from M3 (Brand) onward for browser automation (design validation, screenshot capture, etc.).

**Options:**
- (a) **Skip browser workflows in prototype** — sufficient for demo; M1-M2 don't need browser
- (b) **Wrap Playwright CLI via `exec`** — limited; only static operations (screenshot, PDF), no interactive page control
- (c) **Write a custom Nanobot tool** — register a `PlaywrightTool` that wraps Playwright Python API. Medium effort but gives full browser control.

**Decision deferred** — not blocking M1-M2 or the 2-day prototype.

---
