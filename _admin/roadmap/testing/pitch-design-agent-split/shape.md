# Shape - Pitch Design Agent Split

> **Purpose:** This document captures shaping decisions made during planning and accumulates execution context. The Original Shaping section is immutable. All other sections are append-only during execution.

---

## Original Shaping (Planning Phase)

### Scope Definition

**What this plan accomplishes:**
- Creates a new creative design agent that owns all visual/design work across RBTV
- Merges investor and client pitch workflows into a single parameterized `pitch-creation` workflow
- Splits pitch workflow at step 06/07 boundary — design agent owns steps 07-08
- Splits M3 Brandbook workflow at step 02/03 boundary — design agent owns step 03
- Implements handoff mechanisms for both one-way (pitch) and round-trip (brandbook) patterns
- Updates existing agent menus (Roelof, Leo, Paul) to reflect the split

**What this plan does NOT include:**
- Pitch edit mode (E01/E02) — deferred to future PRD
- Pitch step 09 (Synthesis) ownership — deferred until design agent is tested
- M3 Brandbook step 05 (Synthesis) ownership — deferred
- M3 strategy frameworks 1-6 — stay with Paul, no changes
- Design validation skill integration — separate enhancement
- Orchestrator agent for multi-agent workflows — noted as open challenge, not in scope

### Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Agent scope | Single agent covers both pitch design and brand visual | Visual communication principles apply universally; domain-specific knowledge loaded per workflow |
| Pitch handoff point | After step 06 (Structure) | Step 06 output (slide structure) is natural handoff artifact |
| Brandbook handoff | Option A: mid-workflow agent switch | Simpler, consistent with pitch pattern (Paul → Designer → Paul) |
| Pitch merge approach | Single `pitch-creation` workflow with `pitch_type` parameter | All differences handleable by variable + conditional blocks; eliminates maintaining identical steps across two workflows |
| Phase ordering | Merge first, then create agent, then integrate | Merging first means design agent integrates into ONE workflow instead of two |
| Design agent persona | Visual communication expert (Tufte + brand systems) | Covers both pitch deck and brand identity without being generic |

### Constraints

| Constraint | Source | Impact |
|------------|--------|--------|
| Never Touch BMAD | CLAUDE.md admin restrictions | All changes must be within RBTV repo only |
| Existing activation pattern | Agent consistency requirement | New agent must follow same persona/menu/config.yaml load pattern |
| `{project-root}` path variables | Cross-mode compatibility | Agent and workflow files must use path variables, not hardcoded paths |
| Thin loader pattern | RBTV architecture | Agent needs command + skill + cursor sub-agent files in `_config/.cursor/` |
| Step files are self-contained | Workflow micro-file architecture | Steps loaded one at a time; handoff instructions must be in the step file itself |

### User Inputs (Maintained and Developed)

| # | Input Topic | User's Input | Developed Into |
|---|-------------|--------------|----------------|
| 1 | PRD source | User pointed to `prd-pitch-design-agent-split.md` as the requirements document | Full plan structure derived from PRD's implementation scope and proposed solution |
| 2 | Plan location | "create it in your workspace" → `_admin/roadmap/todos/_claude-code-workspace/` | Plan folder created at workspace location with PRD copied in |

### Collaborative Decisions

| # | Decision | User's Position | AI Contribution | Final Resolution |
|---|----------|-----------------|-----------------|------------------|
| 1 | Plan name | Confirmed `pitch-design-agent-split` | Suggested based on PRD filename | `pitch-design-agent-split` |
| 2 | Plan structure | Confirmed 5-phase structure | Proposed phase ordering (merge → create → integrate pitch → integrate brandbook → cleanup) | 5 phases with merge-first ordering |

---

## Standards Applied

### RBTV Architecture Standards

| Standard | Application in This Plan |
|----------|-------------------------|
| Agent activation pattern | Design agent follows persona → config.yaml → menu → handler pattern |
| Thin loader stack | Command + skill + cursor sub-agent created for design agent |
| Workflow micro-file architecture | Step files remain self-contained with sequential loading |
| `{project-root}` path variables | All file references use path variables from `_config/config.yaml` |

### Admin Restrictions

| Standard | Application in This Plan |
|----------|-------------------------|
| BMAD Component Map Check | Verified no existing BMAD design agent exists |
| Never Touch BMAD | All changes within RBTV repo |
| Minimal Internalization | Design knowledge files already exist in RBTV (`html-patterns.md`, etc.) |

### Plan-Specific Rules

| Rule | Enforcement |
|------|-------------|
| Pitch type parameterization | Merged workflow must support `investor` and `client` via single `pitch_type` variable |
| Handoff instructions in step files | Each split boundary step must contain exact invocation command |
| Round-trip brandbook pattern | Step 03 must return control to Paul for step 04 |

### Tool Mode Selection

| Scenario | Mode | Rationale |
|----------|------|-----------|
| Need prior context | Skill | Preserves conversation history |
| Context saturated | Subagent | Fresh context window |
| Complex validation | Subagent | quality-review needs focused evaluation |
| Quick lookup | Skill | Minimal overhead |
| Already in subagent | Skill only | Subagents cannot nest |

---

## Decisions and Discoveries

> **APPEND-ONLY RULES:**
> 1. Only capture decisions, discoveries, and unexpected constraints — NOT routine task completions
> 2. NEVER modify previous entries
> 3. NEVER delete entries
> 4. Ask yourself: "Will this matter in one month?" If no, don't log it
>
> **What belongs here:** Decisions made during execution (with rationale), discoveries that change prior decisions, unexpected constraints
> **What does NOT belong:** Routine task completions ("created file X", "updated config Y")

<!-- Decisions and discovery entries will be appended below this line -->

### Entry 1: Step 08 asymmetry discovery

**Date:** 2026-03-09 | **Task:** p1-1

**Type:** Discovery

The investor Step 08 ("Visual Identity & Image Prompts") is a comprehensive 9-section file covering brand asset integration, visual enhancement identification, CSS background patterns, and image prompt generation. The client Step 08 ("Generate Image Prompts") is a much simpler 5-section file that only audits existing `<img>` tags and generates prompts. The investor version is the clear superset. Decision: use the investor version as the base for the merged step and add `{pitch_type}` conditionals for client-specific style guidance (conservative B2B tone). The visual enhancement and brand integration capabilities benefit both pitch types.

### Entry 2: Merged workflow output folder strategy

**Date:** 2026-03-09 | **Task:** p1-2

**Type:** Decision

The merged `workflow.md` uses two explicit frontmatter fields (`outputFolder_investor` and `outputFolder_client`) rather than a single `outputFolder` with inline conditional syntax. This makes the frontmatter machine-parseable while the step files use `{pitch_type}` conditionals to select the correct path at runtime. The `pitch_type` parameter itself is set during agent command invocation, not within the workflow.

### Entry 3: P1 checkpoint — APPROVED

**Date:** 2026-03-09 | **Task:** p1-checkpoint

**Type:** Decision

Quality-review subagent evaluated all 12 merged workflow files against 6 criteria (completeness, parameterization, conditional correctness, path variables, micro-file architecture, output routing). All criteria passed. Key validations: step-08 asymmetry correctly resolved using investor superset as base with client conditionals; dual outputFolder frontmatter fields cleanly handle path divergence; conditional syntax consistent across all files. Awaiting human approval to proceed.

### Entry 4: Design agent persona — user brainstorming incorporated

**Date:** 2026-03-09 | **Task:** p2-1

**Type:** Decision

User provided extensive brainstorming for the design agent persona named "Vivian" (originally "Vivid"). The brainstorming defined a "visual poet at the intersection of strategy and beauty" with cinematic communication style, 6 signature traits, and two behavioral modes (Pitch Mode, Brand Book Mode). Decision: compress into BMAD agent template fields (role, identity, communication_style, principles) while keeping the behavioral mode choreography in the workflow step files where it belongs. The PRD's "Tufte craftsman" direction was replaced by the more alive cinematic design sensibility from the user's brainstorming. Agent file created as `agents/vivian.md` with frontmatter `name: "designer"`. 4 principles distilled from 6 traits: obsessively visual, elegantly opinionated, generous collaborator, slightly dramatic.

### Entry 5: Thin loader path correction

**Date:** 2026-03-09 | **Task:** p2-2

**Type:** Discovery

The p2-2 task file referenced `_config/.cursor/sub-agents/` but no such directory exists. The actual pattern uses `_config/.cursor/agents/` (matching `bmad-rbtv-quality-review.md`, `bmad-rbtv-context-distill.md`, `bmad-rbtv-web-research.md`). Created all three loader files using the correct `_config/.cursor/agents/` path. The task file also referenced `agents/designer.md` but the actual file is `agents/vivian.md` — loader files point to `vivian.md`.

### Entry 6: P2 checkpoint — APPROVED

**Date:** 2026-03-09 | **Task:** p2-checkpoint

**Type:** Decision

Quality-review subagent evaluated all 5 deliverables (agent file, command, skill, sub-agent, manifest) against 6 criteria. All criteria passed. Key validations: activation pattern matches roelof.md/paul.md exactly (5-step sequence); thin loader stack complete (3 files in correct `_config/.cursor/` directories); persona emphasizes visual communication with no narrative/strategy overlap; menu covers pitch deck design, pitch images, and brand visual identity; manifest entry has all 4 columns correctly formatted; all references use `{project-root}` path variables. Awaiting human approval to proceed to Phase 3.

### Entry 7: Phase 3 pitch design integration — step 06 handoff + steps 07-08 persona swap

**Date:** 2026-03-09 | **Task:** p3-1, p3-2, p3-3

**Type:** Decision

Three changes implement the pitch workflow split at the step 06/07 boundary:

1. **Step 06** (structure): The `[C] Continue` completion path now contains an AGENT HANDOFF blockquote instructing the narrative agent to tell the user to invoke `@bmad-rbtv-designer` and select `[PD] Pitch Deck Design`. The step file explicitly forbids the narrative agent from loading `{nextStepFile}` itself.

2. **Step 07** (generate): Role reinforcement replaced from "The Investor"/"The Buyer" to Vivian's design persona. A new mandatory sequence step 1 ("Load Slide Structure") added before HTML pattern loading — reads `pitch-narrative.md` and requests the step 06 finalized structure from the user. All HTML generation logic, `pitch_type` conditionals, design knowledge loading, and technical requirements preserved.

3. **Step 08** (images): Role reinforcement replaced from "The Investor"/"The Buyer" to Vivian's design persona with cinematic framing. All visual identity work, brand asset integration, prompt generation, and `pitch_type` conditionals preserved.

### Entry 8: Phase 4 brandbook integration — round-trip handoff (Paul → Vivian → Paul)

**Date:** 2026-03-09 | **Task:** p4-1, p4-2, p4-3

**Type:** Decision

Three changes implement the brandbook workflow split at the step 02/03 boundary with round-trip handoff:

1. **Step 02** (identity): The `[C] Continue` completion path now contains an AGENT HANDOFF blockquote instructing Paul to tell the user to invoke `@bmad-rbtv-designer` and select `[BV] Brand Visual Identity`. The step file explicitly forbids Paul from loading `{nextStepFile}` itself. Menu text updated to "hand off to the design agent for Visual Guidelines".

2. **Step 03** (visual): Role reinforcement replaced from "YC mentor" to Vivian's design persona (Creative Director and Visual Storyteller). All visual identity work preserved — color palette, typography, logo AI prompts, imagery, iconography, iteration loops, prompting knowledge index loading. Return handoff added: after step completion, Vivian instructs the user to invoke `@bmad-rbtv-mentor` and select `[C] Continue Project` for Paul to resume at step 04.

3. **workflow.md**: Added MULTI-AGENT ROUTING section documenting the two-agent pattern (Paul steps 01-02 + 04-05, Vivian step 03) with explicit handoff flow. Step sequence table augmented with Agent column. "Your Role" description updated to reflect multi-agent ownership.

### Entry 9: Phase 5 agent updates, cleanup, and reference validation

**Date:** 2026-03-09 | **Task:** p5-1, p5-2, p5-3, p5-4, p5-5, p5-refs

**Type:** Decision

Six changes complete the cleanup phase:

1. **Roelof (agents/roelof.md)**: Title changed from "Deck Architect" to "Narrative Stress-Tester". Description and menu item [N] updated to reflect steps 01-06 scope with handoff note. Workflow paths updated from `investor-pitch-creation/` to `pitch-creation/` for both create and edit modes.

2. **Leo (agents/leo.md)**: Same pattern as Roelof. Title changed from "Deck Architect" to "Narrative Stress-Tester". Workflow paths updated to merged `pitch-creation/`. Menu item [N] description reflects steps 01-06 scope.

3. **Paul (agents/paul.md)**: Description updated to document brandbook step ownership (01-02, 04-05). New rule added explicitly stating step 03 belongs to Vivian with instruction to follow embedded handoff.

4. **Command loaders**: Both `bmad-rbtv-create-investor-pitch.md` and `bmad-rbtv-create-client-pitch.md` descriptions updated to reflect steps 01-06 scope with design agent handoff. No path changes needed — loaders are thin (point to agent files, which contain the paths).

5. **Old workflow deletion**: `workflows/investor-pitch-creation/` and `workflows/client-pitch-creation/` directories fully removed. Verified non-existent via filesystem check.

6. **Reference validation**: Full codebase search for old `investor-pitch-creation` and `client-pitch-creation` paths confirms zero remaining references in active files. All occurrences are in plan documentation (historical, not to be modified). Verified merged workflow has all 11 step files (9 create + 2 edit). Verified design agent loader stack (3 files). Verified tools-manifest.csv entry. Verified no hardcoded paths. All handoff references (`@bmad-rbtv-designer`, `@bmad-rbtv-mentor`) resolve to valid commands.

### Entry 10: P5 FINAL CHECKPOINT — APPROVED

**Date:** 2026-03-09 | **Task:** p5-checkpoint

**Type:** Decision

Quality-review subagent evaluated all Phase 5 deliverables against 7 criteria. Initial review REJECTED on criterion 7 (learnings.md empty). Learnings populated with 3 entries (PRD path validation, agent naming convention, multi-agent handoff pattern). Re-review passed all 7 criteria. Human approved. Plan execution complete.

---

## References

### Source Documents Analyzed

| Document | Key Insights Extracted |
|----------|----------------------|
| `_admin/roadmap/todos/_claude-code-workspace/prd-pitch-design-agent-split.md` | Full problem statement, proposed solution, implementation scope, risks, success criteria |
| `agents/roelof.md` | Investor pitch agent persona, menu structure, workflow entry point |
| `agents/leo.md` | Client pitch agent persona, menu structure, workflow entry point |
| `agents/paul.md` | Mentor agent persona, M3 brandbook workflow entry |
| `agents/fernando.md` | Reference agent structure pattern for new agent creation |
| `workflows/investor-pitch-creation/workflow.md` | Pitch workflow metadata, step routing, output paths |
| `workflows/client-pitch-creation/workflow.md` | Client pitch workflow — structurally identical to investor |
| `workflows/bi-m3-brandbook/workflow.md` | Brandbook workflow metadata, step routing |

### Files to Load During Execution

| File | Purpose | When |
|------|---------|------|
| `agents/roelof.md` | Update menu for merged workflow and design split | p5-1 |
| `agents/leo.md` | Update menu for merged workflow and design split | p5-2 |
| `agents/paul.md` | Update for brandbook design handoff | p5-3 |
| `agents/fernando.md` | Reference activation pattern for new agent | p2-1 |
| `workflows/investor-pitch-creation/` | Source for merge audit and step merging | p1-1, p1-3 |
| `workflows/client-pitch-creation/` | Source for merge audit and step merging | p1-1, p1-3 |
| `workflows/bi-m3-brandbook/steps-c/step-02-identity.md` | Add handoff to design agent | p4-1 |
| `workflows/bi-m3-brandbook/steps-c/step-03-visual.md` | Refactor for design agent | p4-2 |
| `workflows/_shared/pitch-data/html-patterns.md` | Design knowledge loaded by design agent | p2-1 |
| `workflows/_shared/pitch-data/html-components.md` | Design knowledge loaded by design agent | p2-1 |
| `_config/tools-manifest.csv` | Add design agent entries | p2-3 |
| `_config/.cursor/commands/bmad-rbtv-create-investor-pitch.md` | Loader pattern reference, update for merge | p2-2, p5-4 |
