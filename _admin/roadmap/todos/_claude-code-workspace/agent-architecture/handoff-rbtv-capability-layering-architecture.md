---
title: 'Handoff: RBTV Capability Layering Architecture'
docType: 'handoff'
mode: 'create'
handoffType: 'project'
targetAgent: 'Ana (compound mode) — to formalize the layering framework as one or more backlog PRDs'
stepsCompleted: ['step-01-init.md', 'step-02-location-selection.md', 'step-03-extraction.md', 'step-04-document.md']
inputDocuments:
  - '_admin/roadmap/todos/skills/cp-visual-design-extraction-live-site-access.md'
outputPath: '_admin/roadmap/todos/agent-architecture'
date: '2026-03-11'
---

# Handoff: RBTV Capability Layering Architecture

**Type:** Project
**Created:** 2026-03-11
**For:** Agent creating PRD(s) to formalize the layering framework and guide RBTV's architectural evolution

---

## Context Summary

A strategic analysis of how RBTV organizes and exposes its intelligence to AI agents and humans produced a 6-layer capability framework (L0–L5). All existing RBTV workflows and tasks were classified into these layers, revealing that the system is heavily concentrated at Layer 3 (orchestrated, user-interactive workflows) with almost no reusable building blocks at Layers 1 and 2. This architectural gap prevents agents from composing capabilities — every new use case requires a new monolithic workflow instead of assembling existing primitives.

---

## Problem Being Solved

RBTV has no conceptual framework for understanding at what abstraction level its capabilities should be built. The consequence: capabilities that should be atomic and reusable (navigate a website, take a screenshot, extract CSS, synthesize design tokens) are fused into monolithic workflows that cannot be invoked independently. Agents cannot compose capabilities across domains — if Vivian needs design tokens, she can't call a "get tokens" operation; she'd have to invoke the entire 4-step design-extraction workflow with its menus and halts.

### Current State

- The 6-layer capability framework has been conceptualized and defined
- All existing RBTV workflows (40+) and tasks (9) have been classified into layers
- Strategic gaps have been identified and analyzed
- No implementation has been done — the framework exists only in this handoff and the originating conversation

### Root Cause

RBTV evolved organically, building workflows to solve specific use cases (pitch creation, brandbook, design extraction). Each workflow was designed as a self-contained end-to-end process because there was no architectural guidance for "at what abstraction level should this capability be built?" Everything defaulted to Layer 3 (multi-step, user-interactive workflow), even when the underlying operations were atomic and reusable. The system jumps from L0 (raw platform tools like Playwright) straight to L3 (full workflows) with almost nothing in between.

---

## The Capability Layering Framework

### Two Orthogonal Axes

The framework separates two questions that RBTV previously conflated:

1. **What is the capability?** — The abstraction layer (L0–L5)
2. **How is it accessed?** — The delivery mechanism (skill, command, workflow, task, rule, sub-agent)

These are orthogonal. A Layer 1 operation can be accessed through a skill, directly by a workflow step, or via a command. The layer tells you what abstraction level something lives at. The access pattern tells you how an agent or human reaches it. Not every layer needs every access pattern — some L3 workflows have skills, others are accessible only through commands.

### Layer Definitions

**Layer 0 — Platform Tools**

Raw capabilities provided by the runtime, not by RBTV. Playwright, file system, web search APIs, image generation models, MCP servers. RBTV does not own these but wraps them. L0 defines what is technically possible; RBTV layers above define how those raw capabilities are standardized and composed.

Key principle: RBTV should never reimplement what the platform provides. But it should standardize how agents interact with platform tools (conventions for file paths, output formats, error handling). That standardization is what promotes an L0 tool into an L1 operation.

**Layer 1 — Operations**

Atomic, deterministic, judgment-free. An operation takes clear inputs and produces predictable outputs. It does not decide what to do — it does what it is told.

Characteristics:
- No interpretation or creativity required
- No user interaction during execution
- Reusable across any agent and any workflow
- Agent-agnostic — Vivian and Leo calling the same operation get the same result
- Composable — building blocks for higher layers

Examples: navigate to URL and map links, capture screenshot at viewport, extract CSS rules from loaded page, update config.yaml paths, display available commands.

**Layer 2 — Analysis & Synthesis**

Single-domain interpretation that requires judgment but is still focused and self-contained. It takes raw data (often from Layer 1) and produces structured insight.

Characteristics:
- Requires interpretation — same inputs, different agents might produce different emphases
- Still single-purpose (one analytical lens)
- No multi-step user interaction (may ask for clarification, but not a menu-driven process)
- Reusable across workflows but may be agent-flavored

Examples: synthesize design tokens from screenshots + DOM scans, conduct web research with source evaluation, extract voice signature from text, assess brand visual consistency against a spec, evaluate BMAD compatibility.

Boundary note: Some components sit at the L1/L2 boundary. `context-distill` is a key example — the operation is mechanical (read files, filter content) but the relevance filtering requires interpretation. `ps-lite` is another — it is a conversational analytical capability with a built-in escalation path to Layer 3, making it interactive but not orchestrated.

**Layer 3 — Orchestrated Processes**

Multi-step, user-interactive sequences with state tracking. This is where RBTV's current workflows live. They compose Layer 1 and Layer 2 capabilities into a guided journey with menus, halts, and human decision points.

Characteristics:
- Multi-step with explicit sequencing
- User interaction is structural (menus, confirmations, choices)
- State tracked across steps (frontmatter, output documents)
- Agent-specific (the workflow is designed for a particular agent's perspective)
- Produce deliverables (documents, HTML files, design briefs)

Examples: pitch creation workflow, brandbook framework workflows, design-token extraction workflow, problem structuring, plan lifecycle, BI framework workflows.

**Layer 4 — Cross-Agent Orchestration**

Processes that span multiple agents with explicit handoffs. Each segment is a Layer 3 process owned by one agent; the coordination protocol defines how Agent A's output becomes Agent B's input.

Characteristics:
- Multi-agent with defined handoff boundaries
- Each segment is a Layer 3 process owned by one agent
- Currently, the user manages handoffs manually (invoking the next agent)
- Could evolve toward automated handoffs and shared context passing

Examples: `bi-m3-brandbook` (Paul → Vivian → Paul, round-trip), `pitch-creation` (Leo/Roelof → Vivian, one-way), `bi-business-innovation` (master lifecycle orchestrator spanning milestones that themselves contain multi-agent workflows).

**Layer 5 — Meta-Intelligence**

Capabilities about capabilities. Self-improvement, quality review, planning, compound creation, roadmap management. These operate on RBTV's own artifacts — rules, skills, workflows, tasks.

Characteristics:
- Operates on RBTV's own artifacts
- Reflexive — the system examining and modifying itself
- Not domain-specific (applies across all agents and workflows)
- Clear direction of dependency: L5 examines and modifies L1–L4, but L1–L4 never invoke L5 during their own execution (except quality gates, which are opt-in)

Examples: `quality-review.xml` (evaluates work output), `doc-compound-learning` (creates improvement specs), `bmad-rbtv-create-component` (creates new L1–L4 components), `bmad-rbtv-code-self-improve` (standing instruction to modify layer artifacts).

---

## Complete Classification of Existing Components

### Layer 1 — Operations

| Component | Type | What It Does |
|-----------|------|-------------|
| `tasks/update-bmad-config.xml` | Task | Mechanically update config.yaml paths for RBTV project folder redirection |
| `tasks/restore-bmad-config.xml` | Task | Mechanically restore config.yaml to default BMAD paths |
| `tasks/help.xml` | Task | Scan commands directory, display available commands — pure discovery |
| `tasks/mentor-help.xml` | Task | Read project-memo, display milestone position and progress — read-only |
| `workflows/add-prompting-knowledge/` | Workflow (thin router) | Ask what type → redirect to RBTV Builder with template pre-selected |

### Layer 2 — Analysis & Synthesis

| Component | Type | What It Does |
|-----------|------|-------------|
| `tasks/web-research.xml` | Task | Conduct research with source evaluation, citation standards, trust scoring |
| `tasks/tone-extraction.xml` | Task | Extract voice signature from text — emotional tone, structural patterns, vocabulary |
| `tasks/context-distill.xml` | Task | Read files, filter by relevance to a specific request, return distilled findings (L1/L2 boundary) |
| `tasks/check-bmad-compat.xml` | Task | Evaluate new BMAD release against RBTV touchpoints — compatibility verdict |
| `workflows/ps-lite/` | Workflow (single-step) | Socratic conversational problem structuring — escalates to L3 when complexity warrants |

### Layer 3 — Orchestrated Processes

**Standalone workflows:**

| Component | What It Does |
|-----------|-------------|
| `workflows/problem-structuring/` | Structure problems using MECE, Pyramid Principle, Problem Trees |
| `workflows/design-token-extraction/` | Extract design tokens from website (current: screenshot-only) |
| `workflows/doc-context-handoff/` | Create context transfer summaries for agent continuity |
| `workflows/plan-lifecycle/` | Create self-executing plans with micro-step task files |
| `workflows/prompting-assistance/` | Craft effective prompts using AI model knowledge and techniques |

**BI Framework workflows (all single-agent, all Paul/mentor):**

| Milestone | Frameworks |
|-----------|-----------|
| M1 — Conception | `bi-m1-five-whys`, `bi-m1-jobs-to-be-done`, `bi-m1-competitive-landscape`, `bi-m1-problem-solution-fit`, `bi-m1-lean-canvas`, `bi-m1-working-backwards` |
| M2 — Validation | `bi-m2-technology-readiness-level`, `bi-m2-unit-economics`, `bi-m2-leap-of-faith`, `bi-m2-assumption-mapping`, `bi-m2-pre-mortem`, `bi-m2-tam-sam-som` |
| M3 — Brand | `bi-m3-brand-archetypes`, `bi-m3-golden-circle`, `bi-m3-messaging-architecture`, `bi-m3-tone-of-voice`, `bi-m3-brand-positioning`, `bi-m3-brand-prism` |
| M4 — Prototypation | `bi-m4-design-context`, `bi-m4-user-flow-ia`, `bi-m4-conversion-centered-design`, `bi-m4-heuristic-evaluation` |

**BI Milestone routers:** `bi-m1/`, `bi-m2/`, `bi-m3/`, `bi-m4/` (L3 composing other L3 workflows)

### Layer 4 — Cross-Agent Orchestration

| Component | Agents | Handoff Pattern |
|-----------|--------|----------------|
| `workflows/bi-business-innovation/` | Paul (mentor) | Master lifecycle router across M1–M6; orchestrates milestones that contain multi-agent workflows |
| `workflows/bi-business-innovation/bi-m3/bi-m3-brandbook/` | Paul (01–02, 04–05) → Vivian (03) → Paul | Round-trip: mentor compiles identity, designer creates visuals, mentor synthesizes |
| `workflows/pitch-creation/` | Leo or Roelof (01–06) → Vivian (07–08) | One-way: stress-tester builds narrative, designer generates deck |

### Layer 5 — Meta-Intelligence

| Component | Type | What It Does |
|-----------|------|-------------|
| `tasks/quality-review.xml` | Task | Evaluates work output against quality criteria — APPROVED/REJECTED verdict |
| `workflows/doc-compound-learning/` | Workflow | Create backlog PRDs documenting system improvements — self-reflective analysis |
| Skill: `bmad-rbtv-create-component` | Skill → Workflow | Creates new RBTV components (agents, workflows, tasks, skills) |
| Rule: `bmad-rbtv-code-self-improve` | Rule | Guidelines for continuously improving rules based on emerging patterns |

---

## Strategic Analysis

### Observation 1: Layer 1 Is Underdeveloped

There are only 5 L1 components, and 3 of them are config/help utilities. The system has almost no reusable atomic operations. This is the gap that the visual-design-extraction PRD exposed — navigation, screenshot capture, and DOM extraction should be L1 operations, but they do not exist as standalone components. The system jumps from L0 (raw Playwright) straight to L3 (the full design-extraction workflow).

### Observation 2: Layer 3 Is Dominant

The vast majority of RBTV intelligence lives at L3 — multi-step guided workflows. This makes sense for a system designed around the "mentor guides founder" model, where user interaction at every step is the point. But it means there is very little that agents can invoke programmatically without going through a full user-interactive workflow. When Vivian needs design tokens, she cannot call a "get tokens" operation — she would have to invoke the entire 4-step design-extraction workflow with its menus and halts.

### Observation 3: Layer 2 Is Where Composability Lives

The L2 components (`web-research`, `tone-extraction`, `context-distill`) are the most reusable things in the system. Any agent, any workflow, any context can invoke them. This is the layer that should grow the most if agents are to become more capable without creating more L3 workflows.

### Strategic Takeaway

If RBTV agents are to navigate websites, take screenshots, extract CSS, review designs, and validate pitch fixes — the investment must go into L1 and L2. Build the atomic operations (L1) and analytical capabilities (L2), then let the existing L3 workflows and new ones compose them. The current architecture goes L0 → L3 with almost nothing in between, which is why every new capability ends up as a new monolithic workflow instead of a composable building block.

---

## Practical Impact: What Composability Enables

### New Use Cases From Existing + New L1/L2 Primitives

| Use Case | Agent | L1 Operations Used | L2 Analysis Used |
|----------|-------|-------------------|-----------------|
| Design token extraction (refactored) | Any via skill | site-navigate, page-screenshot, dom-css-extract | design-token-synthesize |
| Design review / audit | Vivian | site-navigate, page-screenshot | design-review (compare against brandbook) |
| Pitch visual QA loop | Leo / Roelof / Vivian | page-screenshot (before/after) | visual-diff (compare before/after) |
| Competitive website analysis | Leo / Roelof | site-navigate, page-screenshot | (agent interprets conversationally) |
| Page discovery / sitemap | Any agent | site-navigate | (none — raw output sufficient) |

The L1 operations (site-navigate, page-screenshot, dom-css-extract) are reused across every use case. Different L2 analysis tasks are composed on top. Different agents bring different judgment to the same building blocks.

### Example Decomposition: Design Token Extraction

**Current (monolithic L3):**
- L3 workflow (4 steps) bundles navigation, screenshot, pixel guessing, and documentation
- Nothing reusable; cannot be invoked for design review or competitive analysis

**Proposed (layered):**
- L1: `site-navigate` — discover pages, return site map JSON
- L1: `page-screenshot` — capture one page at specified viewport, save PNG
- L1: `dom-css-extract` — extract all CSS data from one page, save scan JSON
- L2: `design-token-synthesize` — merge screenshots + scans into consolidated tokens
- L3: Refactored workflow — thin orchestrator that invokes L1/L2, manages user interaction

The workflow becomes lightweight orchestration. The heavy lifting is in independently testable, reusable L1/L2 components.

---

## User Goals

1. Establish the 6-layer capability framework as a formal architectural standard for RBTV
2. Use the framework to guide all future component creation decisions — what layer should this live at? What access pattern should expose it?
3. Decompose existing monolithic L3 workflows into layered, composable components where the decomposition yields reuse value
4. Grow L1 (Operations) and L2 (Analysis & Synthesis) to enable agents to compose capabilities rather than invoke monolithic workflows
5. Enable new use cases (design review, pitch visual QA, competitive analysis) through composition of existing primitives rather than building new monolithic workflows

---

## Constraints Gathered

| Constraint | Type | Description |
|------------|------|-------------|
| Preserve RBTV micro-file workflow architecture | Technical | L3 workflows must continue to use step files, frontmatter tracking, menu halts, and sequential enforcement |
| Access patterns are orthogonal to layers | Architecture | Not every layer needs every access pattern; a Layer 3 workflow might have a skill or might only be accessible through commands |
| L1 operations must be agent-agnostic | Architecture | The same L1 operation called by Vivian or Leo must produce the same result; agent judgment belongs at L2 or higher |
| Support both remote and local targets | Technical | Playwright-based L1 operations must handle both `https://` URLs and local `file://` paths (for pitch HTML review) |
| Session management is agent-level | Technical | Playwright browser sessions are managed by the executing agent within its context window, not by individual L1 tasks |
| Not all L3 workflows need decomposition | Scope | Only decompose when the decomposition yields genuine reuse value; the BI framework workflows (five-whys, lean-canvas, etc.) are fine as L3 |

---

## Decisions Already Made

| Decision | Rationale | Alternatives Rejected |
|----------|-----------|----------------------|
| Six layers (L0–L5) | Captures meaningful distinctions: platform tools, atomic ops, analytical judgment, orchestrated processes, multi-agent coordination, meta-intelligence | Three layers (too coarse — conflates operations with analysis), four layers (missing meta-intelligence and cross-agent orchestration as distinct concerns) |
| Access patterns orthogonal to layers | A skill can surface any layer; a command can invoke any layer; forcing a 1:1 mapping between layers and access patterns would create unnecessary rigidity | Tying specific access patterns to specific layers (e.g. "L1 = tasks only") |
| Agent persona is not a layer | The persona changes how a capability is applied, not what capability exists; it is a lens applied at L2+ | Making persona its own layer (would create confusion about what "invoking a layer" means) |
| L1 and L2 must be available through skills | Skills are the discovery mechanism for agents; if L1/L2 capabilities are not skill-accessible, agents cannot discover them | Only exposing L1/L2 through workflow step instructions (limits ad-hoc use) |
| The visual-design-extraction PRD must reference the broader architecture PRD before execution | The current PRD bundles L1+L2+L3 into a single monolithic workflow redesign; the layered architecture should be established first to guide the decomposition | Executing the current PRD as-is (would perpetuate the monolithic pattern) |
| quality-review and doc-compound-learning are L5 | They operate on RBTV's own artifacts — examining and improving the system itself | Placing them at L2 (they are not single-domain analysis; they are meta-operations on the system) |

---

## Information Gaps

- Exact input/output contracts for proposed L1 Playwright primitives (site-navigate, page-screenshot, dom-css-extract) — these need detailed specification during PRD creation
- Whether the layering framework should be documented as a Cursor rule, a knowledge file, or a standalone architectural document within RBTV
- Priority ordering for decomposition: which existing L3 workflows should be decomposed first for maximum reuse value
- Relationship between this framework and `_config/tools-manifest.csv` — should the manifest track layer classification?
- Whether L4 (cross-agent orchestration) needs formalization beyond the current "instructions in step files telling the user to switch agents" pattern

---

## Work Completed

| Item | Description | Status |
|------|-------------|--------|
| Layering framework definition | 6 layers (L0–L5) with characteristics, examples, and boundary rules | Complete |
| Full RBTV classification | All 40+ workflows and 9 tasks classified into layers | Complete |
| Strategic gap analysis | Three observations + strategic takeaway documented | Complete |
| Composability impact analysis | New use cases enabled by L1/L2 investment identified | Complete |
| Design-token decomposition example | Concrete example showing L1 → L2 → L3 layered architecture | Complete |
| Agent overlap analysis | Vivian, Leo, Roelof relationship to layered capabilities mapped | Complete |

---

## Files to Load

| File | Purpose | Priority |
|------|---------|----------|
| `_admin/roadmap/todos/skills/cp-visual-design-extraction-live-site-access.md` | PRD that triggered this analysis — contains the concrete example of monolithic L3 that needs decomposition; must be updated to reference the new architecture PRD | Reference |
| `workflows/design-token-extraction/workflow.md` | Current monolithic L3 workflow — the primary decomposition candidate | Reference |
| `agents/vivian.md` | Designer agent — primary beneficiary of L1/L2 Playwright primitives | Reference |
| `agents/leo.md` | Client pitch agent — benefits from L1 site navigation for competitive analysis and pitch visual QA | Reference |
| `agents/roelof.md` | Investor pitch agent — same L1 benefits as Leo | Reference |
| `workflows/bi-business-innovation/workflow.md` | Master BI workflow — L4 example for understanding cross-agent orchestration | Reference |
| `workflows/pitch-creation/workflow.md` | Pitch workflow — L4 example with Leo/Roelof → Vivian handoff; candidate for pitch visual QA loop | Reference |

---

## For the Agent Reading This Handoff

### Immediate Next Steps

1. Create a PRD (compound or standalone) that formalizes the 6-layer capability framework as an RBTV architectural standard — including layer definitions, classification criteria, and guidance for "which layer should my new component live at?"
2. Within that PRD or as a companion PRD, specify the first set of L1 operations to build: `site-navigate`, `page-screenshot`, `dom-css-extract` — with detailed input/output contracts
3. Update `_admin/roadmap/todos/skills/cp-visual-design-extraction-live-site-access.md` to add a dependency note: the broader architecture PRD must be reviewed before executing the design-token-extraction redesign

### Guidelines

- The framework should be prescriptive enough to guide future component creation ("I want to add a capability — what layer does it belong at?") but not so rigid that it prevents pragmatic decisions
- Focus the PRD on L1 and L2 growth — these are the strategic investment areas; L3/L4/L5 are adequately served by existing patterns
- Consider whether the classification table in this handoff should be maintained as a living document (e.g., in `_config/` or `_admin/`) that tracks which layer each component belongs to
- The Playwright-based L1 operations are the highest-value first implementation because they unlock multiple new use cases across multiple agents

### What NOT to Do

- Do not attempt to decompose all L3 workflows at once — only decompose when the decomposition yields genuine reuse value across agents or workflows
- Do not create a layer for agent personas — personas are a lens applied at L2+, not a capability layer
- Do not force every component to be accessible through every access pattern — access patterns are orthogonal to layers by design
- Do not treat this as a refactoring project — it is an architectural framework that guides new development and selective decomposition of existing components

---

## Self-Cleanup Instruction

After successfully completing the handoff instructions, consider whether this handoff document is still needed:

- If the work is complete → Delete this handoff file
- If work continues → Update or create a new handoff for the next agent

---

## References

| Reference | Purpose |
|-----------|---------|
| `_admin/roadmap/todos/skills/cp-visual-design-extraction-live-site-access.md` | PRD that triggered the architectural analysis — must be updated with dependency note |
| `_config/tools-manifest.csv` | Current tool/skill registry — may need layer classification column |
