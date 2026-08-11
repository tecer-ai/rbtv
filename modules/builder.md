# Builder

## Purpose

The RBTV-native module. **Its component-creation half was RETIRED 2026-08-11 by owner ruling** — see `builder/RETIRED.md`. What the module still SHIPS is one thing: the source-of-truth rule that keeps edits flowing to the repo instead of to the generated `.claude/` copies. Component structure, naming, and the exposure/seat canon now live in the meta/planning reference set and the forge workflow.

---

## Components

### `source-of-truth` rule

- **What**: An always-on rule stating that RBTV components installed into `.claude/` (skills, commands, rules, subagents) are generated thin loaders or copies, overwritten on every re-install — edits go to the RBTV source repo (module-first paths), then `python install.py` propagates them.
- **When to use**: Always active once the builder module is installed. In workspaces where you BUILD RBTV components, the edit-source-not-installed-copies discipline is load-bearing, not redundant.
- **How to invoke**: Automatic. No trigger — passive context.
- **What it produces**: Changed agent behavior — component edits land in `{rbtv_path}/<module>/...` source paths, never in `.claude/`.

---

## RETIRED components (2026-08-11) — kept for history, never followed

The three below no longer install and carry retirement banners. Details and the supersession:
`builder/RETIRED.md`.

### `rbtv-create-component` — RETIRED

- **What**: Guided builder for any RBTV or vault AI component — skills, workflows, rules, commands, personas, tasks. Acts as a design partner: it challenges assumptions and forces key decisions before writing any file. Handles both RBTV-standard components (placed in the RBTV source repo, module-first) and workspace-native components (placed per that workspace's CLAUDE.md conventions).
- **When to use**: Creating a new skill, workflow, or rule from scratch. Modifying an existing component. Trying to understand how a component is structured before editing it. Use this instead of manually exploring component directories — the workflow handles discovery. NOT for trivial text-only corrections to an existing component (stale reference, obsolete caveat, typo) that change no structure, frontmatter, steps, or behavior — edit those directly.
- **How to invoke**: "Create a new skill for X" or "build a workflow for Y" — or invoke by name: `rbtv-create-component`.
- **Inputs / outputs**:
  - Input: component type, description of what it should do, target system (RBTV or workspace-native)
  - Output: correctly placed and structured component file(s) with compliant naming and size
- **Draft refinement**: at the scaffold step the workflow runs a prompt-refinement pass (`data/prompt-refinement-checklist.md`) over the drafted instructions before finalizing them — surfacing hidden assumptions, vague wording, missing context, missing constraints, and unforced clarifications so the component's text holds up when executed literally.
- **Efficiency gate**: every build ends at `step-05-efficiency-gate.md` — the new files are measured (`component-review/scripts/measure-component.py`) and checked against the Create-Time Gate in `component-review/data/efficiency-patterns.md` (single authority, determinism, discrete triggers, named consumers, event-scoped load, size limits, light path, bounded reasoning load). Violations are fixed or explicitly owner-accepted, never silently shipped.
- **Example**: "I need a skill that runs our weekly competitor scan" → Claude identifies the right component type, drafts the structure, confirms placement, writes the files.

---

### `component-review` workflow (review mode of `rbtv-create-component`) — RETIRED

- **What**: Token-efficiency diagnosis of an existing component — any RBTV module, or any component in a workspace with a CLAUDE.md. Four steps: intake (target + owner's felt-waste hypotheses), measure (deterministic baseline via `scripts/measure-component.py` — words, imperative/conditional/arbitration density, longest prose run, open-deliberation cues, cross-file loads, duplicated blocks), investigate (read-only sonnet sub-agents, one lane per cost locus), synthesize (problem tree + hypothesis verdicts + ranked format fixes).
- **When to use**: A component feels expensive to run — agents seem to read or reason too much to execute it — and you want measured evidence of where the cost lives before trimming. The owner's hypotheses are tested, not assumed: felt waste and measured waste routinely diverge.
- **How to invoke**: "Review {component} for token efficiency" / "diagnose why {component} is expensive" — routes through the `rbtv-create-component` skill's Review mode.
- **Inputs / outputs**:
  - Input: the target component (name or path; installed loaders are resolved to source)
  - Output: an efficiency-diagnosis document — measured baseline, discoveries with KEEP counter-evidence rows, LOAD/DECIDE/THINK/RECORD/COORDINATE problem tree, verdicts, prioritized fixes sized for planning handoff
- **Core constraint**: the quality floor — protections keep their value; only their delivery format is on trial. The taxonomy lives in `component-review/data/efficiency-patterns.md`, the single source consumed by both this workflow and the create-flow gate.

---

### `measure-component.py` tool (`exposure.csv`) — ORPHANED

The component-review measurement CLI still runs and is still the module's one `exposure.csv` row, but its owning workflow is retired. Left in place rather than dropped silently from the tool inventory.
