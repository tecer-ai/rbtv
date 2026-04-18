---
title: 'Compound: bmad-rbtv-create must use manifests instead of hardcoding lists'
docType: 'compound'
mode: 'create'
stepsCompleted: ['step-01-init', 'step-02-self-assessment', 'step-03-discussion', 'step-04-document']
inputDocuments: []
outputPath: '.docs/compound/'
date: '2026-02-04'
yoloMode: false
---

# bmad-rbtv-create must use manifests instead of hardcoding lists

**Type:** Rule / Constraint  
**Priority:** High  
**Status:** Backlog

---

## Overview

### Problem

When the Builder agent (invoked via `bmad-rbtv-create`) generates files (agents, workflows, steps, tasks, commands, etc.), it may instruct those files to reference "all commands", "all skills", "all rules", or similar open-ended lists. Hardcoding such references leads to:

- **Maintenance burden** — When new commands, skills, or rules are added, every file that enumerates them must be updated manually.
- **Drift** — Generated files quickly become outdated as the system evolves.
- **Single source of truth** — No canonical list exists; different files may list different subsets or use different wording.

### Goals

1. **bmad-rbtv-create must never produce files** that hardcode references to "all commands", "all skills", "all rules", or equivalent (e.g. "every command", "the full list of skills", "all rules in .cursor/rules").
2. **When a generated file needs to reference a catalog** of commands, skills, rules, subagents, or similar, the Builder must **refer to a manifest** (CSV or equivalent) as the single source of truth.
3. **If no manifest exists** for that catalog, the Builder must **document that a manifest should be created** (or create it as part of the build instructions) so that maintenance is easier.

### Constraints

- Rule applies to output of `BMAD/.cursor/commands/bmad-rbtv-create-component.md` (Builder agent).
- Manifests already in use (e.g. `tools-manifest.csv`, `subagents-manifest.csv`) must be referenced rather than duplicating their content in generated files.
- No change to Builder behavior in this document — documentation only; implementation is backlog.

---

## Self-Assessment

### Error Analysis

**What went wrong:** No single rule was documented that forbids hardcoding catalog-style lists in Builder-generated files and requires manifest references instead.

**Why it matters:** Without this rule, templates and build instructions can keep producing files that enumerate commands/skills/rules by name or path, causing maintenance overhead and drift as the system grows.

### Context Source Evaluation

- **Builder agent** (`agents/fernando.md`) — Produces agents, workflows, steps, tasks, commands, configs, knowledge, registries.
- **Templates** (`workflows/build/templates/`) — Used by Builder; may contain or suggest hardcoded lists.
- **tools-manifest.csv** — Canonical list of commands, skills, workflows, tasks, subagents; should be the reference for "what exists".
- **subagents-manifest.csv** — Canonical list of subagent ids; example of manifest-based reference (e.g. in plan-creation-rules).

### Improvement Options

1. **New Rule (Builder activation or rules)**  
   - Add an explicit rule: "Never hardcode in generated files references to 'all commands', 'all skills', 'all rules' or similar; reference a manifest instead; if no manifest exists, specify that one must be created."  
   - **Rationale:** Makes the constraint discoverable and enforceable when the Builder runs.  
   - **Location:** Builder agent rules, or a dedicated rule file loaded by Builder.

2. **Template Guardrails**  
   - Update Builder templates (e.g. ide-loader-template, agent-template, workflow-template) to include a reminder or placeholder: "Reference manifest at [path]; do not list items inline."  
   - **Rationale:** Reduces chance of hardcoding at the point of generation.  
   - **Location:** `workflows/build/templates/*.md`.

3. **Manifest-First Checklist**  
   - Add a step in the Builder flow or in the build knowledge file: before generating any file that needs a catalog, check "Does a manifest exist for this? If not, create or specify manifest first."  
   - **Rationale:** Ensures manifests are created when missing.  
   - **Location:** `workflows/build/data/bmad-architecture.md` or Builder activation steps.

4. **Documentation-Only (this compound)**  
   - Document the rule in a compound PRD (this document) for backlog implementation. No code or template changes.  
   - **Rationale:** Captures the requirement; implementation can follow in a separate task.  
   - **Location:** `.docs/compound/compound-bmad-create-use-manifests.md`.

5. **Validation Task**  
   - Add a post-generation check (or separate task) that scans Builder output for phrases like "all commands", "all skills", "all rules" and flags them.  
   - **Rationale:** Catches violations automatically.  
   - **Location:** New task or step in build workflow.

---

## Proposed Solution

**Selected option:** Combination of **Option 1 (New Rule)** and **Option 3 (Manifest-First Checklist)** for implementation. **Option 4 (this document)** is the documentation deliverable; no development is executed here.

### Specification

1. **Rule to be added (when implementing)**  
   - **Where:** Builder agent rules or a rule file that the Builder loads (e.g. in build data or cursor rules).  
   - **Text (or equivalent):**  
     - "When generating files that reference a catalog of commands, skills, rules, subagents, or similar, NEVER hardcode the list (e.g. 'all commands', 'every skill', 'all rules')."  
     - "ALWAYS refer to the appropriate manifest (e.g. tools-manifest.csv, subagents-manifest.csv) as the single source of truth; use manifest path and column names (e.g. 'id', 'path') in instructions."  
     - "If no manifest exists for that catalog, the generated file MUST state that a manifest should be created (or the Builder must create it) so that maintenance is easier."

2. **Manifest-first checklist (when implementing)**  
   - In Builder activation or build knowledge: before generating a file that needs to reference commands/skills/rules/subagents, the Builder must:  
     - Check if a manifest for that catalog exists (e.g. tools-manifest.csv, subagents-manifest.csv).  
     - If yes: reference that manifest in the generated file.  
     - If no: either create the manifest or document in the generated file that a manifest must be created and used.

3. **Scope**  
   - Applies to all files produced by the Builder when following `bmad-rbtv-create` (agents, workflows, steps, tasks, IDE commands, configs, knowledge, registries).  
   - "Hardcoding" includes: inline lists of command names, skill names, rule paths, or instructions like "read all files in .cursor/commands".

### Implementation Details

| Aspect | Details |
|--------|---------|
| File(s) to modify/create | Builder agent or build rules; optionally `workflows/build/data/bmad-architecture.md`; templates only if adding reminders. |
| Scope of change | Add one rule + one checklist step; no change to existing manifest formats. |
| Related files | `BMAD/.cursor/commands/bmad-rbtv-create-component.md`, `agents/fernando.md`, `tools-manifest.csv`, `subagents-manifest.csv`. |

---

## Rationale

- **Single source of truth:** Manifests (CSV or similar) already exist for rbtv (tools-manifest.csv, subagents-manifest.csv). Using them in generated files keeps catalogs up to date in one place.  
- **Easier maintenance:** When a new command, skill, or rule is added, only the manifest is updated; no need to edit multiple generated files.  
- **Consistency with current practice:** Plan-creation-rules and execution protocol already reference `subagents-manifest.csv` instead of hardcoding subagent names; this compound generalizes that pattern to commands, skills, and rules.

---

## Acceptance Criteria

- [ ] A rule exists (in Builder or loaded by Builder) that forbids hardcoding "all commands", "all skills", "all rules" (or equivalent) in generated files.
- [ ] The rule requires referencing a manifest when a catalog is needed; if no manifest exists, require or document its creation.
- [ ] Builder flow or build knowledge includes a manifest-first check before generating files that reference catalogs.
- [ ] No implementation is performed in this compound — documentation only; implementation is done in a separate development task.

---

## Related Files

| File | Relationship |
|------|--------------|
| BMAD/.cursor/commands/bmad-rbtv-create-component.md | Command that loads Builder; rule applies to its output. |
| agents/fernando.md | Builder agent; candidate location for rule or reference to rule. |
| tools-manifest.csv | Example manifest for commands, skills, workflows, tasks, subagents. |
| subagents-manifest.csv | Example manifest for subagent ids; referenced by plan-creation-rules. |
| workflows/plan-lifecycle/data/plan-creation-rules.md | Example of referencing manifest instead of hardcoding (subagents). |

---

## References

- User request: compound that bmad-rbtv-create must never hardcode references to "all commands, skills, or rules" or similar; when that happens, a manifest should be created (if not available) so maintenance is easier. Only document; do not execute development.
- Compound workflow: `workflows/doc-compound-learning/workflow.md`.
- Ana agent: `agents/ana.md`.

---

## Discussion Notes

- **Documentation only:** User explicitly requested that only the rule be documented in a compound PRD; no development (no changes to Builder, templates, or manifests) is to be executed in this step.
- **Implementation:** Acceptance criteria and proposed solution describe what should be done when the backlog item is implemented; the deliverable here is the compound PRD itself.
