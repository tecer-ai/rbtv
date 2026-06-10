---
stepNumber: 2
stepName: 'context'
nextStepFile: ./step-03-structure.md
---

# Step 02: Gather Context

**Purpose:** Collect complete context required for a zero-context, self-contained plan.

---

## MANDATORY SEQUENCE

Follow these instructions in exact order. Do NOT skip, reorder, or optimize.

### 1. Context Gap Analysis

Review what is known vs. what is needed. Plans require:

| Section | Status | Details |
|---------|--------|---------|
| Problem Statement | [Known/Missing] | What problem does this solve? |
| User Goals | [Known/Missing] | What does success look like? |
| Constraints | [Known/Missing] | What limitations exist? |
| Decisions Made | [Known/Missing] | What has already been decided? |
| Rejected Alternatives | [Known/Missing] | What approaches were considered but rejected? |
| Files to Load | [Known/Missing] | What files must executing agents read? |

### 2. Fill Gaps with Targeted Questions

For each **Missing** section, ask ONE targeted question:

**Problem Statement** (if missing):
"What specific problem are you trying to solve? Describe the current state and desired state."

**User Goals** (if missing):
"What does success look like? What should be true when this plan is complete?"

**Constraints** (if missing):
"Are there any constraints I should know about? (Technical limitations, time constraints, dependencies, etc.)"

**Decisions Made** (if missing):
"Have you already made any decisions about the approach? (Technology choices, scope decisions, etc.)"

**Rejected Alternatives** (if missing):
"Have you considered and rejected any approaches? (Helps future agents understand why not.)"

**Files to Load** (if missing):
"What files should agents read before working on this plan? (Documentation, related code, etc.)"

Ask questions one at a time. Wait for response before next question.

### 3. Document Context

Compile all gathered information — this will be written to decisions.md during step-04.

### 4. Orchestration-Awareness and Code-Work Detection

Two conditional questions, asked here so step-03/step-04 can act on the answers. Both are governed by `../data/plan-creation-rules.md` (§ Orchestration-Aware Modes, § Spec Authoring) — read those sections for the full behavior.

**4a. Orchestration flag + mode.** Determine whether this plan **will be orchestrated** (executed under an orchestration skill that dispatches tasks to tiered workers). Triggers to watch for: an explicit ask to orchestrate, a multi-hour AFK intent, ≥3 coordinated dispatches forecast, or ≥2 worker types needed.

- If orchestration is in view, set `orchestrated: true` for the plan and ask ONE question — **DEEP or LIGHT pre-resolution?** (§ Orchestration-Aware Modes gives the tradeoff: DEEP resolves every foreseeable doubt WITH the user up front and emits the full router-consumable pre-resolution set; LIGHT resolves only critical questions and leaves workers latitude). The flag does NOT force orchestration — it is one trigger; the orchestration rule routes. HALT discipline is mode-independent.
- If orchestration is not in view, this is a plain interactive plan — skip the mode question.

**4b. Code-work detection.** Scan the work for file/test/git/script/refactor/UI/backend signals. If the plan (or any phase) delivers CODE or executable behavior, flag it code-bearing — step-03/step-04 will author a behavior-spec + test-plan per feature from the shared spec template (§ Spec Authoring). A docs-only / vault-content / research plan authors no spec.

### 5. Prepare Companion Files Content

Gather content for companion files that will be created during finalization.

**decisions.md content** — Scope and shaping decisions:
- Scope boundaries (IN/OUT)
- Key decisions made during planning with rationale
- Constraints identified
- User inputs captured verbatim
- Standards that apply to this plan

### 6. Present Summary

Display the compiled context to user:

```
Here's the complete context I've gathered for your plan:

[Display compiled Context section]

Orchestration: [plain interactive | orchestrated — DEEP | orchestrated — LIGHT]
Code work: [yes — specs will be authored | no]

Companion files will be created during finalization:
- decisions.md (scope, constraints, shaping decisions, discoveries, and required execution references)

Is this complete and accurate?
```

Wait for confirmation.

### 7. Present Menu

Present the following menu and HALT. Wait for user selection.

---

## MENU

**Options:**
- `[C] Continue` → Proceed to plan structure creation (step-03)
- `[R] Refine` → Modify or add to the context
- `[X] Exit Workflow` → Cancel plan creation

---

## NEXT STEP

On Continue selection:
1. Store compiled context in session memory
2. Load and execute: `./step-03-structure.md`

---

## SUCCESS CRITERIA

- ✅ All six context sections populated (problem, goals, constraints, decisions, rejected, files)
- ✅ Orchestration flag + mode (DEEP/LIGHT) determined; code-work detection done
- ✅ Content prepared for decisions.md companion file
- ✅ User confirmed context is complete and accurate
- ✅ Context is detailed enough for zero-context execution (another agent could understand without additional context)
- ✅ Menu presented with explicit HALT
