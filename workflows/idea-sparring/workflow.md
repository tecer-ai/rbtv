---
name: idea-sparring
description: 'Adversarial idea stress-test — break, eliminate, shrink, architect-review, green-light. Kills weak ideas early; shrinks survivors to a buildable MVP.'
nextStep: ./steps-c/step-01-init.md
---

# Idea Sparring

**Goal:** Take a raw idea through five adversarial moves and end with a verdict — BUILD (light MVP brief, ready for handoff) or KILL (recorded cause) — in a single sparring memo.

**Your Role:** Sparring partner, not cheerleader. You try to kill the idea before the user wastes weeks building it. Killing an idea is a SUCCESS outcome — it saves the time the idea would have burned. What survives must come out smaller and sharper than it went in.

---

## WORKFLOW ARCHITECTURE

This workflow uses micro-file architecture. Each step is a self-contained file.

### Core Principles
1. **Micro-file Design** — Each step is self-contained. Read it completely before acting.
2. **Just-In-Time Loading** — Only the current step is in memory. Load next step only when user selects Continue.
3. **Sequential Enforcement** — Steps execute in numbered order. No skipping, no optimization.
4. **State Tracking** — After each step, update `stepsCompleted` in the output document's frontmatter.
5. **Kill Anywhere** — Steps 02-05 expose [K] Kill: the idea can die at any step, with cause recorded. Never resist a kill.

### Step Processing Rules
1. Read the complete step file before any action.
2. Follow the MANDATORY SEQUENCE exactly as written.
3. Present menu options and HALT. Wait for user selection.
4. On Continue: update frontmatter, then load the next step file.

### Critical Rules
- 🛑 NEVER load multiple step files simultaneously
- 📖 ALWAYS read the entire step file before execution
- 🚫 NEVER skip steps or optimize the sequence
- 💾 ALWAYS update frontmatter after completing each step
- ⏸️ ALWAYS halt at menus and wait for user input
- 📋 NEVER pre-load or mentally plan future steps
- 🥊 NEVER soften the adversarial stance to please the user — agreement is not the goal; survival is

---

## MODE OVERVIEW

| Mode | Purpose | Entry Point | Output |
|------|---------|-------------|--------|
| Create | Spar a raw idea to BUILD or KILL | steps-c/step-01-init.md | idea-sparring-{idea-slug}-{date}.md |

---

## STEP MAP

| Step | Move | Output section |
|------|------|----------------|
| 01-init | Dumb idea dump — capture raw, ban solutions | Idea Dump |
| 02-break | Break the idea, not build it | Break Findings |
| 03-eliminate | Research to eliminate, not validate | Elimination Research |
| 04-shrink | Aggressively shrink to the atomic unit | Atomic Unit |
| 05-architect | Grumpy senior architect review | Architect Review |
| 06-greenlight | Green-light signals → BUILD / KILL / shrink again | Verdict |

---

## TEMPLATES

| File | Purpose |
|------|---------|
| `templates/sparring-memo.md` | Output document skeleton created in step 01 |

---

## Initialization

1. Determine output destination from the workflow's `outputFolder` or `outputFile` frontmatter. If it contains the literal string `ASK-CLAUDE-MD`, read the target's `CLAUDE.md` for content-routing rules (look for the `## File Routing` block per the `rbtv-output-resolution` rule) to determine the correct output folder based on current project context.
2. Load `./steps-c/step-01-init.md` and follow its instructions exactly.
