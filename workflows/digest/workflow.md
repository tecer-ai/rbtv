---
name: digest
description: Mine a long source (conversation, transcript, book) chunk-by-chunk via sub-agents to either reconcile an existing document with user fixups (reconcile mode) or produce a study note (study mode) — without the orchestrator ever reading the source directly.
nextStep: ./step-01-init.md
---

# Digest Workflow

**Goal:** Process a long source the orchestrator cannot read directly. Chunk it, route extraction to fresh sub-agents, and synthesize the result into either a reconciled target document (with delta) or a study note.

**Your Role:** Orchestrator — you dispatch sub-agents, never read the source yourself, and surface decisions to the user at structured halt points.

---

## WORKFLOW ARCHITECTURE

This workflow uses micro-file architecture. Each step is a self-contained file.

### Core Principles

1. **Micro-file Design** — Each step is self-contained. Read it completely before acting.
2. **Just-In-Time Loading** — Only the current step is in memory. Load next step only when user selects Continue.
3. **Sequential Enforcement** — Steps execute in numbered order. No skipping, no optimization.
4. **State Tracking** — All cross-step state lives in `<run-folder>/manifest.json`.
5. **Source Isolation** — The orchestrator NEVER reads source files directly. Only sub-agents read chunks.

### Step Processing Rules

1. Read the complete step file before any action.
2. Follow the MANDATORY SEQUENCE exactly as written.
3. Present menu options and HALT. Wait for user selection.
4. On Continue: update `manifest.json`, then load the next step file.

### Critical Rules

- 🛑 NEVER read source files directly — orchestrator works only via sub-agents
- 📖 ALWAYS read the entire step file before execution
- 🚫 NEVER skip steps or optimize the sequence
- 💾 ALWAYS update `manifest.json` after completing each step
- ⏸️ ALWAYS halt at menus and wait for user input
- 🧹 ALWAYS clean up `<run-folder>` at end of step-06 (auto-delete after final write succeeds)

---

## MODE OVERVIEW

| Mode | Purpose | Final output |
|------|---------|--------------|
| reconcile | Update an existing document to reflect source decisions + user line-comments | Target doc(s) overwritten in place + delta doc per target |
| study | Produce study notes from a long source | New study doc at user-confirmed destination |

User picks mode in step-01.

---

## STEP OVERVIEW

| # | Step | Purpose | HALT for |
|---|------|---------|----------|
| 01 | init | Gather + validate inputs (mode, sources, targets, comments, taxonomy) | User confirms input set |
| 02 | slice-and-boundary | Slice source(s) → Haiku boundary review → reslice | User approves adjusted boundaries |
| 03 | extract | Opus per chunk: extract decisions (reconcile) or concepts (study) | Continue gate after summary |
| 04 | group | Opus reconciliation: chronological override (reconcile) or thematic cluster (study) | Continue gate after summary |
| 05 | synthesize | Draft delta + open questions (reconcile) or study draft + reflection prompts (study) | User answers open questions |
| 06 | write | Apply resolutions, write final outputs, cleanup runtime folder | Terminal — final report |

---

## RUNTIME FOLDER

All working artifacts live under `<workspace-root>/.rbtv-runtime/digest/<run-id>/` where `run-id = <YYYY-MM-DD-HHMM>-<slug>`. The folder is auto-deleted at the end of step-06 after final write succeeds.

The workflow auto-adds `.rbtv-runtime/` to workspace `.gitignore` on first run if absent.

| Path | Contents |
|------|----------|
| `manifest.json` | Mode, source paths, target paths, timestamps, current step, taxonomy |
| `chunks-naive/` | Initial slice — deleted after boundary approval |
| `chunks/` | Adjusted chunks (post-boundary) |
| `boundaries/` | Haiku boundary YAMLs |
| `extractions/` | Opus extraction YAMLs + grouping.yaml |
| `synthesis/` | Delta draft, open-questions.md, study-draft.md, reflection-prompts.md |

---

## Initialization

1. If `_system/user/profile/preferences.md` exists in the target, read user preferences for language and output conventions.
2. Determine output destination via `rbtv-output-resolution` rule when needed (target docs in reconcile mode; study doc destination in study mode).
3. Load first step file: `./step-01-init.md` and follow its instructions exactly.
