---
stepsCompleted: ['step-01-init', 'step-02-discovery', 'step-03-success', 'step-04-journeys', 'step-05-domain-skipped', 'step-06-innovation-skipped', 'step-07-project-type', 'step-08-scoping', 'step-09-functional', 'step-10-nonfunctional', 'step-11-polish', 'step-12-complete']
inputDocuments:
  - '_bmad-output/robotville-v4.0/founder/project-memo.md'
  - '_bmad-output/robotville-v4.0/founder/m1-conception/lean-canvas.md'
  - '_bmad-output/robotville-v4.0/founder/m1-conception/working-backwards.md'
  - '_bmad-output/robotville-v4.0/founder/m1-conception/problem-solution-fit.md'
  - '_bmad-output/robotville-v4.0/founder/m1-conception/jobs-to-be-done.md'
workflowType: 'prd'
documentCounts:
  briefs: 0
  research: 0
  brainstorming: 0
  projectDocs: 0
  founderDocs: 5
classification:
  projectType: 'SaaS (B2C) - messaging-delivered AI platform'
  domain: 'General / AI-powered business services'
  complexity: 'low'
  projectContext: 'hybrid - brownfield system (RBTV), greenfield delivery layer'
---

# Product Requirements Document - Robotville v4.0

**Author:** Henri
**Date:** 2026-02-13

## Executive Summary

Robotville v4.0 adds a messaging-based delivery layer to BMAD + RBTV, making structured AI-guided business innovation accessible through Slack (and later WhatsApp) instead of the Cursor IDE. Users interact with specialized AI agents — Mentor (22 business frameworks across 6 milestones), DomCobb (problem structuring), and Doc (documentation) — through chat commands on their phone.

**Differentiator:** End-to-end thinking-to-building pipeline via messaging. The same system that challenges business assumptions (M1-M3) also guides the build (M4-M6). No code, no IDE, no consultants.

**Target Users:** Aspiring first-time business creators (25-50) with domain expertise but no startup experience or technical skills — at the moment they cross from daydreaming to active intent.

**Prototype Goal:** Working demo for VC meeting in ~2 weeks. Validation MVP proving the core thesis: RBTV works outside an IDE, accessible to non-technical users through messaging.

**Architecture:** `_mobile/` adapter layer inside `_bmad/rbtv/` translates existing RBTV workflows to Nanobot runtime structure. Single VPS, Slack Socket Mode (outbound-only), file-based persistence via project-memo, allowlist access control. One codebase, two delivery channels — messaging is a feature of RBTV, not a fork.

## Success Criteria

### User Success

- User opens Slack, invokes Mentor, and completes a full business innovation framework with the same output quality as the Cursor experience
- User can invoke DomCobb for problem structuring mid-workflow
- User can invoke Doc (compound mode only) to document findings/issues on mobile
- Frameworks accessed through existing RBTV commands — no new UX to learn beyond the Slack interface
- Shared channels enable co-founder collaboration; separate channels/DMs provide independent sessions
- (Post-prototype) User can list project output files and receive file contents directly in Slack chat

### Business Success

- Working prototype demoed to VCs within ~2 weeks — proves AI competence and product potential
- System supports multiple concurrent allowlisted users for testing
- Validates the core thesis: RBTV works outside an IDE, accessible to non-technical users through messaging
- Lean Canvas metrics (M1 completion >20%, Day 1→Day 2 return >30%, free→paid 5-10%) apply post-prototype — not prototype gates

### Technical Success

- Nanobot + Slack integration runs stable on a single VPS supporting up to 5 concurrent users
- Nanobot runtime uses the HKUDS distribution (`https://github.com/HKUDS/nanobot`) on the latest stable release for deployment parity
- `_mobile/` adapter layer successfully translates RBTV workflows to Nanobot structure
- Playwright wrapped via shell exec for M3+ browser-dependent steps
- Allowlist-based access control prevents unauthorized users
- Response latency acceptable (within 30s including AI provider time, no hard threshold on provider portion)
- (Post-prototype) Install script (`git pull` → run script → deployed) works for updates

### Measurable Outcomes

- End-to-end: user runs full Working Backwards framework through Slack, output quality matches Cursor
- Up to 5 allowlisted users can run sessions simultaneously without cross-contamination
- Agent switching (Mentor ↔ DomCobb) preserves workflow state across transitions
- System auto-recovers from crashes without manual intervention

## User Journeys

### Journey 1: Carla — First-Time Founder, Full Pipeline (M1→M6)

**Carla**, 34, restaurant manager in São Paulo. 15 years in food service. Has been thinking about a local food delivery concept for months — talks about it at the bar, friends say "you should do that!" Nothing ever happens.

**Opening Scene.** Carla's friend sends her a Slack invite link to the Robotville workspace. She opens Slack on her phone, joins, and lands in `#welcome`. A pinned message reads:

> Welcome to Robotville! Here's everything you need:
>
> **`mentor`** — Start or continue your business innovation journey (22+ frameworks, M1-M6)
> **`domcobb`** — Get help structuring a problem or thinking through something you can't articulate
> **`doc`** — Document learnings, bugs, or insights
> **`files`** — See what project files have been created
>
> To begin, open any channel and type `mentor`.

No jargon. No overwhelming list. Five commands. Carla types `mentor`.

**Rising Action — The Thinking (M1-M3).** The Mentor agent greets her, asks about her idea. No forms, no vocabulary she doesn't know. Just a conversation. "Tell me about this idea. Who's the customer?" Twenty minutes later, she's answered questions she never thought to ask herself. The Mentor says: "I've saved your Working Backwards document. Type `files` to see all your project documents, or just ask me to show you a specific one." She types `files` — a clean list appears.

Over the next week, in 20-minute sessions on the bus and before bed, the Mentor walks her through Working Backwards, Jobs-to-be-Done, Problem-Solution Fit, Lean Canvas, Competitive Landscape, Five Whys. Each framework builds on the last. She requests a file at one point — the Mentor posts the raw content in chat with a note: "This is in Markdown format — it may look a bit raw here, but the content is what matters. Focus on the substance."

Through M2, the Mentor helps her validate assumptions — which ones are existential, which can wait. She maps her TAM, pressure-tests unit economics, runs a pre-mortem. Through M3, she defines her brand: archetype, positioning, tone of voice, messaging architecture. The Mentor challenges every vague answer.

At one point she's stuck on competitive positioning. She types `domcobb`. The agent switches context, helps her extract what she knows intuitively through lateral questions. Ten minutes later, she returns to `mentor` — the Mentor picks up exactly where it left off.

**Climax — The Building (M4-M6).** This is the transition no other tool provides. The same Mentor that challenged her assumptions now guides her to build. In M4, the system takes her validated concept, brand identity, and customer definition and generates a working prototype — a real food delivery app for her neighborhood. Not a landing page. A functioning product where customers can browse her menu, place orders, and she can manage deliveries. She reviews it in Slack: the Mentor sends her screenshots and asks for feedback. She requests changes in plain language: "customers should be able to filter by dietary restrictions." The Mentor adjusts.

Through M5, she puts the working prototype in front of real customers in Vila Madalena — market validation with an actual product, not a survey. In M6, the Mentor orchestrates the final build. A live product appears at `robotville.ai/app/vila-delivery`. Carla opens it on her phone. It works. Customers can order. She can fulfill.

**Resolution.** Carla shares the link with her first ten customers. "I built this." She didn't write a line of code. She didn't open a laptop. She didn't hire a developer or pay a consultant. She went from a bar napkin to a functioning digital product with validated business model, brand identity, and real customers — and the only interface she ever touched was her messaging app.

---

### Journey 2: Carla — Getting Stuck, Edge Case

**Same Carla**, mid-way through Problem-Solution Fit. The Mentor asks her to define her competitive landscape. She freezes — she knows her competitors by instinct but can't articulate what makes them different or why her concept wins.

**The friction point.** She types something vague: "there are other delivery apps but mine is different." The Mentor pushes back: "How specifically? What do they offer that you don't, and vice versa?" She's stuck. Doesn't know how to frame it.

**Recovery.** She types `domcobb`. The agent switches context. DomCobb doesn't ask about competitors — it asks: "Tell me about the last time you ordered delivery and were disappointed. What happened?" Through a series of lateral questions, DomCobb helps Carla extract what she knows intuitively but can't articulate. Ten minutes later, she has three concrete differentiators.

She types `mentor` to return. The Mentor picks up exactly where it left off — the project-memo state is intact. She completes the competitive section with confidence.

---

### Journey 3: Henri & Guilherme — Co-Founder Collaboration

**Henri** and **Guilherme**, co-founders of Robotville. Both in the same Slack channel, testing the system with their own project idea as a stress test.

**Opening Scene.** Henri types `mentor` in the shared channel. The Mentor greets and begins Working Backwards. Guilherme jumps in with a clarification on the customer definition. The Mentor incorporates both inputs — it doesn't distinguish between speakers, it treats the conversation as collaborative input.

**Rising Action.** They work through the framework together, challenging each other's assumptions in real-time. Henri types a customer definition; Guilherme pushes back in the chat; the Mentor synthesizes both perspectives. It feels like a three-way strategy session.

**Climax.** They hit a disagreement on pricing. Henri says $10/mo, Guilherme says $20/mo. The Mentor doesn't pick sides — it asks: "What evidence supports each price point? What would you need to see to resolve this?" They document both hypotheses with falsification tests.

**Discovering bugs.** Mid-session, the Mentor loses context after a long exchange — a consolidation event triggered. Henri types `doc` and selects compound mode to document the issue: what happened, what they expected, what broke. The doc is saved to the project output files. They'll fix it later.

**Resolution.** By end of session, they've stress-tested the prototype, validated the collaborative flow works, documented 3 bugs, and have a real Working Backwards document produced entirely through Slack.

**Noted gap (future):** When Carla in Journey 1 wants to invite a co-founder or advisor, collaborative access must be as simple as sharing a link. Slack handles this natively for now, but this requirement must be preserved when expanding to WhatsApp — don't design into a corner where collaboration requires admin intervention.

---

### Journey 4: Henri — System Admin

**Henri**, managing the VPS and Robotville infrastructure.

**Setup.** Henri has a VPS running. He clones the BMAD repo and manually sets up the workspace: copies the BMAD mirror, moves RBTV into place, copies `_mobile/` bootstrap files to the Nanobot workspace root, sets up skills, and applies the config template. (Post-prototype: `install.py` automates this process.)

**Security configuration.** Henri configures the VPS firewall: block ALL inbound traffic except SSH (restricted to his IP only). No HTTP, no HTTPS, no other open ports — Slack Socket Mode is outbound-only, so the VPS needs no public-facing services. IP scanners find nothing because nothing is listening. API keys and Slack tokens are stored in a `.env` file with restricted permissions (`chmod 600`), referenced by Nanobot config via environment variables. No secrets in committed files. For production, migrate to SOPS (Mozilla) or HashiCorp Vault.

**Slack configuration.** He creates the Slack app (Socket Mode), adds the bot token and app token to the `.env` file. Configures the allowlist with his and Guilherme's Slack user IDs. Uses the HKUDS Nanobot runtime on latest stable release and runs `nanobot gateway`.

**Monitoring.** Nanobot posts a startup message to `#admin`: "Robotville online. Nanobot v{version}, {n} skills loaded, allowlist: {count} users." Henri sees the confirmation on his phone — the system is live. A watchdog cron job runs every 5 minutes: checks if the Nanobot process is alive, auto-restarts if dead, and posts a notification to `#admin`: "Nanobot restarted at {time}." This is the safety net for the VC demo — if it crashes at 3am, it recovers automatically. Henri can also type `status` (admin-only command) in Slack to check: system uptime, active sessions, last activity timestamp.

**Ongoing operations.** A new RBTV framework is added to the main repo. Henri runs `git pull` on the VPS and manually updates the workspace. (Post-prototype: re-runs install script for automated updates.) The new framework is available to users immediately.

**Adding testers.** A new tester needs access. Henri adds their Slack user ID to the allowlist in the config.

---

### Journey Requirements Summary

| Journey | Capabilities Revealed |
|---------|----------------------|
| Carla — Full Pipeline | `#welcome` channel with simplified commands, Mentor agent via Slack, session persistence across days, file listing command, file content delivery in chat with markdown disclaimer, project-memo state tracking, DomCobb agent switching, full M1-M6 end-to-end pipeline |
| Carla — Getting Stuck | DomCobb agent switching, seamless return to Mentor with state intact, agent context isolation |
| Henri & Guilherme — Collaboration | Shared channel multi-user input, Doc compound for bug documentation, context consolidation behavior. **Future gap:** collaborative access must remain link-simple when expanding to WhatsApp |
| Henri — System Admin | Manual VPS setup (install script post-prototype), `git pull` + manual update workflow, allowlist management, Slack app configuration, `#admin` channel with startup notification, watchdog auto-restart cron, `status` admin command |

**Security requirements (cross-cutting):** See NFR4-NFR8 for full specification. Summary: no inbound ports except SSH (restricted IP), secrets in env vars only, allowlist access control, VPS not discoverable via scanning.

## SaaS (B2C) Messaging Platform — Technical Requirements

### Project-Type Overview

Robotville v4.0 is a messaging-delivered AI platform — a conversational SaaS product where the entire user experience occurs inside a messaging app (Slack for prototype, WhatsApp planned). There is no web dashboard, no traditional UI. The "application" is the conversation itself, with AI agents executing structured business innovation workflows and producing file-based outputs.

### Technical Architecture (Prototype)

**Runtime:** Single Nanobot instance on a single VPS. All users share the same server and process.

**Session Model:** Sessions isolated by `channel:chat_id` — each Slack DM or channel thread is a separate session with its own conversation history, memory, and project state. No per-user filesystem isolation, no database-level separation. Known limitation: cross-contamination risk if two users share a channel. Acceptable for F&F/VC testing where users are briefed on this constraint. Production requires proper multi-tenant architecture (see PSF-7).

**Access Control:** Allowlist of Slack user IDs. All allowlisted users get full, unrestricted access — no tier enforcement, no feature gates, no usage limits in prototype. Unauthorized users are silently ignored.

**Data Persistence:** Purely file-based, two-layer design:
- **Project-memo files** (primary state): Each project has a `project-memo.md` with frontmatter tracking `currentMilestone`, `currentFramework`, `stepsCompleted`, and all project-specific state. This is the canonical source of truth for workflow continuity. Agents read project-memo before every response and update it after every framework completion. Project-memo data must NOT be duplicated into MEMORY.md — doing so bloats context and creates divergence risk.
- **Nanobot memory system** (conversational context only): MEMORY.md for long-term conversational facts, HISTORY.md for searchable log. These handle agent personality and general user preferences — not project state.
- **Project output files**: Markdown documents produced by each framework, stored in the project's output folder on the VPS filesystem.
- No database. No external storage. Backup strategy: filesystem snapshots or rsync.

### Integration Architecture

| Integration | Protocol | Prototype Status |
|-------------|----------|-----------------|
| Slack | Socket Mode (WebSocket, outbound-only) | Primary — build now |
| WhatsApp | Node.js bridge via Baileys | Planned — post-prototype |
| AI Provider | Via Nanobot (OpenRouter, Anthropic, OpenAI, DeepSeek supported) | Required — provider TBD |
| Playwright | Shell exec wrapper for browser-dependent steps | MVP — available for M3+, not exercised in M1-M2 demo |

No additional integrations for prototype: no analytics platforms, no monitoring services beyond the watchdog cron + `#admin` channel notifications, no external data sources beyond Nanobot's built-in `web_search` and `web_fetch` tools.

### Subscription & Tier Model

| Tier | Prototype | Production (Planned) |
|------|-----------|---------------------|
| Free | N/A — no tiers | 1 project, full M1, site at `robotville.ai/app/{project}` |
| Paid (~$10/mo) | N/A — no tiers | Additional projects, M2-M6 access, tiered AI model access (e.g., faster/cheaper vs. more capable models) |
| Deployment ($30-50) | N/A — no tiers | Custom domain deployment |
| Access control | Allowlist only | Open registration with isolation |

### Implementation Considerations

- **VPS sizing:** Single server supporting up to 5 concurrent F&F/VC testers. No horizontal scaling needed for prototype.
- **State recovery:** If Nanobot crashes, watchdog cron auto-restarts. Session state survives restart (persisted per `channel:chat_id`). Project-memo frontmatter provides external state checkpoint regardless of memory window.
- **Deployment:** `git pull` + `install.py` re-run for updates. No CI/CD pipeline needed for prototype.
- **Security:** All inbound ports blocked except SSH (IP-restricted). Secrets in `.env` with `chmod 600`. Slack Socket Mode is outbound-only — VPS has no public-facing services.

## Project Scoping & Phased Development

### MVP Strategy & Philosophy

**MVP Approach:** Validation MVP — prove the core thesis (RBTV works outside an IDE, accessible to non-technical users through messaging) with a working prototype for VC demo. Not revenue-generating, not feature-complete. The minimum that makes VCs say "this has potential" and F&F testers say "this actually works."

**Resource Requirements:** 2 founders, ~2-day build. Single VPS. No external hires or services beyond AI provider API access.

### MVP Feature Set (Phase 1 — Prototype)

**Core User Journeys Supported:**
- Carla (Journey 1) — partial: M1 framework execution through Slack, DomCobb switching, file output
- Carla (Journey 2) — full: getting stuck, DomCobb recovery, return to Mentor with state intact
- Henri & Guilherme (Journey 3) — partial: shared channel collaboration, Doc compound for bug documentation
- Henri (Journey 4) — full: VPS setup (manual), Slack config, monitoring, allowlist management

**Must-Have Capabilities:**

| Capability | Rationale |
|-----------|-----------|
| `_mobile/` adapter layer (RBTV → Nanobot translation) | Core architecture — without this, nothing works |
| Nanobot bootstrap files (AGENTS.md, SOUL.md, TOOLS.md, USER.md) | Agent identity, routing, and rules |
| Command routing: Mentor, DomCobb, Doc (compound only) | Minimum agent set for VC demo. Doc compound-only is a deliberate design cut — other Doc modes are less useful on mobile, while compound serves to develop the system itself |
| Slack integration via Socket Mode | Primary delivery channel |
| Allowlist-based user access | Security gate for prototype |
| Playwright wrapped via shell exec | Required for M3+ browser-dependent steps. Must be available even if not demoed in M1-M2, to prove full pipeline capability |
| Watchdog cron + `#admin` channel notifications | Safety net for VC demo — auto-restart if crash at 3am |
| `status` admin command | Henri needs to check system health from phone |
| Project-memo state tracking with SOUL.md rule | Workflow continuity across sessions and consolidation events |

**Deferred from MVP (available day 3-4 if time allows):**

| Capability | Reason for Deferral |
|-----------|---------------------|
| File listing command | Can demo without it — user can ask Mentor about project state |
| File content sending in chat | Nice-to-have for mobile UX, not critical for VC demo |
| `install.py` automation script | Manual VPS setup acceptable for single prototype server |

### Post-MVP Features

**Phase 2 (Growth — Post-Prototype):**
- File listing and file content delivery in Slack chat
- Install script for reproducible VPS setup (`git pull` → run script → deployed)
- All RBTV agents/commands beyond Mentor + DomCobb + Doc
- WhatsApp integration
- Per-user project isolation (multi-tenant architecture)
- Onboarding experience design (PSF-2: first interaction must beat comfort zone)
- Context window optimization (increase `memory_window`, test consolidation behavior)

**Phase 3 (Vision — Future):**
- Full M1-M6 pipeline accessible to non-technical users on mobile
- `robotville.ai/app/{project}` deployment pipeline from mobile
- Custom domain deployment ($30-50 fee)
- Subscription billing with tiered model access (~$10/mo) via Pix Automatico (Brazil) and standard payment
- Portfolio gallery of deployed projects as organic marketing
- Structured business data from completions improving AI quality

### Risk Mitigation Strategy

**Technical Risks:**

| Risk | Impact | Mitigation |
|------|--------|------------|
| Context window consolidation destroys mid-framework state (PSF-8) | Broken workflows, lost progress | Project-memo as external state checkpoint; SOUL.md rule to read project-memo before every response; project data excluded from MEMORY.md to avoid bloat |
| Nanobot crashes during VC demo | Demo failure | Watchdog cron auto-restarts every 5 minutes; `#admin` channel alerts; manual SSH fallback |
| Playwright shell exec doesn't cover needed browser operations | M3+ workflows broken | Acceptable risk — M1-M2 demo doesn't depend on browser; validates basic shell exec wrapper first |
| Nanobot project abandoned (~4K lines, small OSS) | Runtime dependency risk | Low urgency — fork if needed; codebase is small enough to maintain |

**Market Risks:**

| Risk | Impact | Mitigation |
|------|--------|------------|
| VCs don't see the product potential | Fundraising fails | Demo focuses on end-to-end journey, not feature list. Show Carla's story live |
| F&F testers abandon after first session (PSF-2) | No validation signal | Monitor Day 1→Day 2 return rate. If <30%, first interaction design needs rework before open beta |

**Resource Risks:**

| Risk | Impact | Mitigation |
|------|--------|------------|
| 2-day build takes longer | Misses VC demo window | MVP is already cut to minimum. Deferred items (file listing, install script) bought back 4-8 hours |
| Single VPS fails | All users offline | VPS provider with SLA; manual SSH restart; no HA needed for prototype scale |

## Functional Requirements

### Agent Interaction

- FR1: User can invoke the Mentor agent through a chat command in Slack
- FR2: User can invoke the DomCobb agent through a chat command in Slack
- FR3: User can invoke the Doc agent (compound mode only) through a chat command in Slack
- FR4: User can converse with an active agent through natural language messages
- FR5: Agents can deliver opinionated pushback — challenging weak thinking rather than validating it

### Workflow Execution

- FR6: Mentor agent can guide a user through structured business innovation frameworks in sequential order across milestones (M1-M6)
- FR7: Each completed framework produces a structured markdown document saved to the user's project output folder
- FR8: DomCobb agent can help users structure ambiguous problems through lateral questioning
- FR9: Doc agent (compound mode) can capture findings, bugs, or insights as structured documentation
- FR10: Agents can perform browser-dependent operations (screenshots, page interaction) for M3+ brand and prototype workflows

### Session & State Management

- FR11: User can resume a workflow across sessions — picking up exactly where they left off, even days later
- FR12: System tracks current milestone, current framework, and completed steps in project-memo frontmatter
- FR13: Agent reads project-memo state before every response to maintain workflow continuity
- FR14: Agent updates project-memo immediately after every framework completion
- FR15: Project-specific state is stored exclusively in project-memo files, not duplicated into conversational memory
- FR16: Workflow state survives system restarts without data loss

### Agent Switching

- FR17: User can switch from one agent to another mid-session by invoking a different command
- FR18: When switching agents, the previous agent's workflow state remains intact
- FR19: User can return to the previous agent and resume from the exact point they left

### Access Control

- FR20: Only allowlisted users can interact with the system
- FR21: Unauthorized users' messages receive no response (silent rejection)
- FR22: Admin can add or remove users from the allowlist through configuration

### System Administration

- FR23: (Deferred) Admin can check system health (uptime, active sessions, last activity) via a Slack command
- FR24: (Deferred) System posts a startup notification to an admin channel when it comes online
- FR25: System automatically restarts if the runtime process dies
- FR26: (Deferred) System posts a notification to the admin channel when an auto-restart occurs
- FR27: System can be updated by pulling new code and reapplying configuration on the VPS

### Collaboration

- FR28: Multiple users in a shared Slack channel can interact with the same agent session
- FR29: Agent synthesizes multi-user input as collaborative conversation — not distinguishing between speakers

### File & Output Management

- FR30: System preserves the existing RBTV/Business Innovation file output structure — no new output management to create
- FR31: (Deferred) User can request a list of their project output files via chat command
- FR32: (Deferred) User can request file contents delivered directly in Slack chat

## Non-Functional Requirements

### Performance

- NFR1: System acknowledges user messages within 2 seconds of receipt (before AI processing begins)
- NFR2: Full agent responses complete within 30 seconds under normal conditions — noting that response time is dominated by AI provider latency, which is outside system control
- NFR3: System must support a maximum of 5 concurrent user sessions on a single VPS

### Security

- NFR4: No API keys, tokens, or secrets stored in committed files — all secrets in environment variables with restricted file permissions
- NFR5: VPS accepts no inbound connections except SSH, restricted to specific IP addresses
- NFR6: Slack communication uses Socket Mode (outbound WebSocket only) — no public-facing ports or services
- NFR7: Only allowlisted Slack user IDs can trigger agent responses
- NFR8: User project files are stored on the VPS filesystem with standard OS-level permissions — no additional encryption required for prototype

### Reliability

- NFR9: System auto-restarts within 5 minutes of a process crash (watchdog cron interval)
- NFR10: All workflow state (project-memo, framework outputs) survives process restarts without data loss
- NFR11: (Deferred) Admin is notified via `#admin` Slack channel on both startup and auto-restart events
- NFR12: No formal uptime SLA for prototype — target is "stays up, recovers automatically if it doesn't"

### Integration

- NFR13: Slack Socket Mode connection must reconnect automatically after network interruptions (handled by Nanobot gateway)
- NFR14: AI provider failures surface as user-visible error messages, not silent failures
- NFR15: System degrades gracefully if AI provider is temporarily unavailable — session state is preserved, user can retry
