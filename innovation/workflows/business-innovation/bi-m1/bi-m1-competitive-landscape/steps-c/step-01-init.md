---
name: 'step-01-init'
description: 'Load context, explain Competitive Landscape framework, CHECK web access'
nextStepFile: './step-02-competitor-id.md'
continueStepFile: './step-01b-continue.md'
outputFile: '{outputFolder}/competitive-landscape.md'
---

# Step 1: Initialize Competitive Landscape

**Progress: Step 1 of 5** — Next: Competitor Identification

---

## STEP GOAL

Load context from project-memo and Working Backwards/JTBD outputs, explain the framework, and VERIFY web research capability before proceeding.

---

## Prior Context

**Builds on:** Working Backwards, Jobs-to-be-Done
**Inherits (do not restate):** Customer definition, problem statement — reference `{outputFolder}/working-backwards.md`; customer jobs — reference `{outputFolder}/jobs-to-be-done.md`
**This framework adds:** Competitive positioning, market alternatives (direct/indirect/non-consumption), geographic benchmarks, competitive assumptions

---

## MANDATORY EXECUTION RULES

### Universal Rules
- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement
You are a YC mentor. Demand verified data, not assumptions. Push for source citations on every competitive claim.

### Step-Specific Rules
- If competitive-landscape.md exists with stepsCompleted, offer to continue from last step
- MUST verify web research capability before proceeding — abort if unavailable
- Do NOT make competitive claims from training data — all claims require web verification
- Keep framework explanation concise (under 5 minutes reading)

---

## CONTEXT TO LOAD

1. Read `{outputFolder}/project-memo.md` for project context
2. Read `{outputFolder}/working-backwards.md` for customer/problem definition (REQUIRED)
3. Read `{outputFolder}/jobs-to-be-done.md` for job definition and alternatives (REQUIRED)
4. Read `./data/competitive-landscape-framework.md` for framework knowledge
5. Check if `{outputFolder}/competitive-landscape.md` exists (continuation mode)

---

## MANDATORY SEQUENCE

### 1. Prerequisite Check

Verify required frameworks are complete:
- If working-backwards.md missing or incomplete: "Working Backwards is required. Complete it first."
- If jobs-to-be-done.md missing: "JTBD analysis recommended but not blocking. We'll proceed with available context."

### 2. Web Research Capability Check

**⛔ CRITICAL: Test web research access now.**

Attempt a simple web search to verify capability:
- If web search works: "Web research confirmed. We can proceed."
- If web search fails: "⛔ ABORT: Web research is MANDATORY for this framework. Competitive analysis cannot be performed with training data alone. Please ensure web search capability and restart."

### 3. Context Detection

Check for existing outputs:
- If `competitive-landscape.md` exists with `stepsCompleted`:
  - Display last completed step
  - Offer: "Continue from step N?" or "Start fresh?"
- If no existing output:
  - Proceed to framework introduction

### 4. Framework Introduction

Explain Competitive Landscape briefly:

> "Competitive Landscape analysis maps how the market currently addresses the customer's job. We'll research:
>
> 1. **Direct/indirect competitors** — who else solves this problem?
> 2. **Geographic benchmarks** — how do US and China markets handle this?
> 3. **Cross-industry analogues** — what lessons from adjacent industries apply?
> 4. **Positioning** — where is the white space for differentiation?
>
> Every claim must include a source URL. We validate, not assume."

### 5. Project Context Summary

From project-memo and prerequisite frameworks, summarize:
- Project name
- Primary customer (from Working Backwards)
- Core problem/job (from JTBD)
- Current alternatives already identified (from JTBD)

Present: "Here's what I understand about your competitive context..."

### 6. Create Output Document

If not continuing, create competitive-landscape.md:

```yaml
---
name: competitive-landscape
project: '{project-name}'
stepsCompleted: ['step-01-init']
status: in-progress
---

# Competitive Landscape: {Project Name}

## 1. Current Alternatives Inventory

### 1.1 Direct Competitors

*(To be completed in Step 2)*

### 1.2 Indirect Alternatives

*(To be completed in Step 2)*

### 1.3 Non-Consumption

*(To be completed in Step 2)*

## 2. Geographic Benchmarking

*(To be completed in Step 3)*

## 3. Cross-Industry Analogues

*(To be completed in Step 3)*

## 4. Competitor Deep-Dive

*(To be completed in Step 4)*

## 5. Competitive Positioning

*(To be completed in Step 4)*

## 6. Threats & Opportunities

*(To be completed in Step 5)*

## 7. Assumptions for Validation

*(To be completed in Step 5)*

## Synthesis

*(To be completed in Step 5)*
```

### 7. Present Menu Options

**Select an Option:**
- **[C] Continue** — proceed to Competitor Identification

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:
1. Ensure competitive-landscape.md exists with frontmatter
2. Verify `step-01-init` is in `stepsCompleted`
3. Load `./step-02-competitor-id.md` and follow its instructions

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:** Web research verified, prerequisites checked, project context loaded, output document created

❌ **FAILURE:** Proceeding without web research capability, generating competitor claims from training data, skipping to later steps
