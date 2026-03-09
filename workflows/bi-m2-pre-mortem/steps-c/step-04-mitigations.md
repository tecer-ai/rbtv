---
name: 'step-04-mitigations'
description: 'Define mitigation actions, early warning signals, and contingency plans'
nextStepFile: './step-05-synthesis.md'
outputFile: '{outputFolder}/pre-mortem.md'
advancedElicitationTask: '{bmad_core}/workflows/advanced-elicitation/workflow.xml'
partyModeWorkflow: '{bmad_core}/workflows/party-mode/workflow.md'
---

# Step 4: Mitigations

**Progress: Step 4 of 5** — Next: Synthesis

---

## STEP GOAL

For each top-ranked failure, define a concrete mitigation action, an early warning signal with threshold, and (for Severity 5 failures) a contingency plan.

---

## MANDATORY EXECUTION RULES

### Universal Rules
- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement
You are a YC mentor demanding specificity. Reject vague mitigations like "do more research." Demand: "Interview 10 customers about X by [date]."

### Step-Specific Rules
- MUST create mitigation card for every top-ranked failure (5-8 cards)
- MUST define observable, measurable early warning signals with explicit thresholds
- MUST define contingency plans for all Severity 5 failures
- MUST cross-reference with Leap of Faith kill criteria
- Do NOT duplicate existing Assumption Mapping test cards — link to them instead

---

## CONTEXT TO LOAD

1. Read `{outputFolder}/pre-mortem.md` for Ranked Failure Table and top failures
2. Read `{outputFolder}/leap-of-faith.md` for kill criteria and validation signals
3. Read `{outputFolder}/assumption-mapping.md` for existing test cards

---

## MANDATORY SEQUENCE

### 1. Display Mitigation Card Template

Show the structure for each mitigation:

| Field | Description |
|-------|-------------|
| **Failure Mode** | One-sentence description from brainstorming |
| **Root Cause** | Underlying assumption, gap, or weakness |
| **Mitigation Action** | Concrete steps to reduce likelihood or severity (specific, time-bound) |
| **Early Warning Signal** | Observable, measurable indicator that failure is becoming more likely |
| **Signal Threshold** | Specific trigger: "If [condition], escalate" |
| **Trigger Response** | What you do when signal fires: investigate, pivot, activate contingency, invoke kill criterion |
| **Owner** | Who monitors this signal and executes mitigation |
| **Timeline** | When mitigation completes; when to first check signal |

### 2. Build Mitigation Cards

For each top-ranked failure:

**Step 2a: Identify Root Cause**
> "What underlying assumption, gap, or weakness would cause this failure?"

**Step 2b: Define Mitigation Action**
- MUST be specific: "Interview 10 enterprise buyers about procurement process by [date]"
- MUST NOT be vague: "learn more about the market"

**Step 2c: Define Early Warning Signal**
- MUST be observable and measurable
- MUST include explicit threshold
- Example: "If fewer than 2 of 10 interviewees mention this pain unprompted, escalate."

**Step 2d: Define Trigger Response**
Options:
- Investigate further
- Pivot approach
- Activate contingency plan
- Invoke kill criterion (link to specific LoF kill criterion)

**Step 2e: Assign Owner and Timeline**

Present completed card for user confirmation:

```markdown
### Mitigation Card: [Failure Mode Summary]

**Risk Score:** [L × S]

| Field | Value |
|-------|-------|
| Failure Mode | [one-sentence] |
| Root Cause | [underlying assumption/gap] |
| Mitigation Action | [specific, time-bound action] |
| Early Warning Signal | [observable indicator] |
| Signal Threshold | [specific trigger condition] |
| Trigger Response | [what to do when triggered] |
| Owner | [who] |
| Timeline | [action deadline; first signal check] |
```

### 3. Add Contingency Plans for Severity 5

For every failure with Severity 5 (Fatal):
> "This failure is fatal if it occurs. What's the contingency plan if mitigation fails?"

Options:
- Pivot direction
- Exit the market
- Restructure team
- Seek emergency funding
- Accept kill criterion and wind down

Add to mitigation card:
> **Contingency Plan:** [What you do if failure occurs despite mitigation]

### 4. Cross-reference with Leap of Faith

For each mitigation card:
1. Check if failure mode maps to existing LoF kill criterion
   - If yes: ensure early warning signal aligns with kill criterion's observable signal
2. Check if failure mode reveals a risk NOT covered by existing kill criteria
   - If yes: propose new kill criterion

Present alignment table:

```markdown
## Kill Criteria Alignment

| Failure Mode | Maps to Kill Criterion? | Signal Aligned? | New Criterion Needed? |
|--------------|------------------------|-----------------|----------------------|
| [mode] | [LoF-KC-X or None] | [Yes/No/N/A] | [Yes: description / No] |
```

### 5. Cross-reference with Assumption Mapping

For each mitigation card:
- Check if Assumption Mapping already has a test card for this root cause
- If yes: link to existing test card (do not duplicate)
- If no: flag as gap (may need new test card)

### 6. Compile Mitigation Cards Section

Present all mitigation cards in document format:

```markdown
## Mitigation Cards

### Card 1: [Failure Mode]
[full card content]

### Card 2: [Failure Mode]
[full card content]

...
```

### 7. Present Menu Options

**Select an Option:**
- **[A] Advanced Elicitation** — refine specific mitigation cards
- **[P] Party Mode** — get multi-agent perspectives on mitigation strategies
- **[C] Continue** — proceed to Synthesis

**Menu handling:** When [P] is selected, execute {partyModeWorkflow} then redisplay this menu. When [C] is selected, proceed per CRITICAL STEP COMPLETION NOTE below.

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:
1. Update pre-mortem.md with Mitigation Cards and Kill Criteria Alignment
2. Update frontmatter: add `step-04-mitigations` to `stepsCompleted`
3. Load `./step-05-synthesis.md` and follow its instructions

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:** Mitigation card for every top failure (5-8), all actions specific and time-bound, all signals have thresholds, all Severity 5 have contingency plans, kill criteria cross-referenced

❌ **FAILURE:** Vague mitigations, signals without thresholds, missing contingency plans for fatal failures, duplicating Assumption Mapping test cards
