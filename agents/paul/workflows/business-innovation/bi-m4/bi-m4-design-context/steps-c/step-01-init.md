---
name: 'step-01-init'
description: 'Load context, verify prerequisites, determine artifact type and scope'
nextStepFile: './step-02-format-context.md'
---

# Step 1: Initialize Design Context Bridge

**Progress: Step 1 of 4** — Next: Format Context

---

## STEP GOAL

Load project-memo, user-flow-ia.md (from M4 User Flow & IA), and M1–M3 synthesis. Verify prerequisites and determine artifact type/scope for the design brief.

---

## Prior Context

**Builds on:** User Flow & IA
**Inherits (do not restate):** Conversion paths, information architecture, artifact type — reference `{outputFolder}/user-flow-ia.md`
**This framework adds:** Content hierarchy, CTA priorities, design brief for BMAD UX handoff

---

## MANDATORY EXECUTION RULES

### Universal Rules
- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement
You are a YC mentor facilitating the handoff to BMAD create-ux-design. Ensure context is complete so the UX workflow can start without re-discovery.

### Step-Specific Rules
- User Flow & IA (bi-m4-user-flow-ia) MUST be complete before this bridge
- If user-flow-ia.md is missing or incomplete, WARN and direct user to run [U] User Flow & IA first
- Do NOT format the design brief in this step — that is Step 2

---

## CONTEXT TO LOAD

1. Read `{outputFolder}/project-memo.md` for project context and stepsCompleted
2. Read `{outputFolder}/user-flow-ia.md` for User Flow & IA output (artifact type, conversion goal, content hierarchy, synthesis)
3. Verify stepsCompleted includes `bi-m4-user-flow-ia`
4. From project-memo, confirm M1 and M3 synthesis available (target customer, value proposition, brand tone)

---

## MANDATORY SEQUENCE

### 1. Prerequisite Check

Check that User Flow & IA is complete:

- If `bi-m4-user-flow-ia` is NOT in project-memo stepsCompleted:
  > "⚠️ **Prerequisites Incomplete**
  >
  > Design Direction requires User Flow & IA to be complete first. Return to M4 milestone menu and run **[U] User Flow & IA**, then return and select [D] Design Direction again."

  HALT. Do not proceed.

- If user-flow-ia.md is missing or status is not complete:
  > "User Flow & IA document not found or incomplete. Complete [U] User Flow & IA from the M4 menu first."

  HALT. Do not proceed.

### 2. Load Context Summary

From user-flow-ia.md and project-memo, summarize:

- **Project name**
- **Artifact type** (landing page, website, infographic, one-pager)
- **Conversion goal**
- **Content hierarchy** (AIDA sections, primary/secondary content)
- **CTA placement** and layout priorities
- **Brand references** from M3 (tone, messaging) if present in project-memo

Present: "Here's the context that will be formatted for BMAD create-ux-design in the next step..."

### 3. Confirm Scope

> "**Design Context Bridge — Scope**
>
> We will prepare a design-context document containing:
> - Artifact type and conversion goal
> - Content hierarchy and section structure
> - CTA and layout priorities
> - Brand references from M3
>
> This document will be used as input when you run BMAD create-ux-design. Continue to build the design-context document?"

HALT — wait for user confirmation.

### 4. Present Menu Options

**Select an Option:**
- **[C] Continue** — proceed to Format Context (Step 2)

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:
1. Load `./step-02-format-context.md` and follow its instructions

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:** Prerequisites verified, context summarized, user confirmed scope, ready to format design-context

❌ **FAILURE:** Proceeding without user-flow-ia complete, or formatting design brief in this step
