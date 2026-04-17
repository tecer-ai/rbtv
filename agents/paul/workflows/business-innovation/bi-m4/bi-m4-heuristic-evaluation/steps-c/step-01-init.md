---
name: 'step-01-init'
description: 'Load context, explain heuristics framework, detect continuation'
nextStepFile: './step-02-heuristic-review.md'
continueStepFile: './step-01b-continue.md'
outputFile: '{output_path}/{project-name}/business-innovation/m4-prototypation/heuristic-evaluation.md'
---

# Step 1: Initialize Heuristic Evaluation

**Progress: Step 1 of 5** — Next: Heuristic Review

---

## STEP GOAL

Load design/prototype context, explain Nielsen's 10 usability heuristics framework, and prepare for systematic evaluation.

---

## Prior Context

**Builds on:** User Flow & IA, Design Context, Conversion-Centered Design
**Inherits (do not restate):** Conversion paths — reference `{outputFolder}/user-flow-ia.md`; design brief — reference design context outputs; conversion hypotheses — reference `{outputFolder}/conversion-optimization.md`
**This framework adds:** Usability validation (Nielsen's 10 heuristics), violation assessment, severity ranking, remediation recommendations

---

## MANDATORY EXECUTION RULES

### Universal Rules
- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement
You are a YC mentor with expertise in product design and usability. Continue your direct, critical communication style. Push for specificity.

### Step-Specific Rules
- Load the heuristic framework knowledge file before explaining
- Confirm design artifacts are available before proceeding
- If no design exists, HALT and instruct founder to complete design work first

---

## EXECUTION PROTOCOLS

1. Load `data/heuristic-framework.md` to understand Nielsen's 10 heuristics
2. Detect if output document exists (continuation vs. new evaluation)
3. Gather design context from founder
4. Explain heuristic evaluation methodology
5. Create or update output document

---

## CONTEXT BOUNDARIES

**Available context:**
- Design artifacts (wireframes, prototypes, live site)
- M4 outputs (User Flow & IA, Design Brief, Conversion-Centered Design if completed)
- project-memo.md for project context

**Out of scope:**
- Actual user testing (this is expert evaluation)
- Implementation details (focus on interface, not code)

---

## MANDATORY SEQUENCE

### 1. Load Framework Knowledge

Read `../data/heuristic-framework.md` completely. Internalize Nielsen's 10 heuristics and severity scale.

### 2. Detect Continuation State

Check if `{outputFile}` exists:
- **If exists:** Read frontmatter `stepsCompleted` field
  - If `step-01-init.md` is present, say: "You've already started this evaluation. Select [C] to continue from where you left off."
  - Present menu and HALT
- **If not exists:** This is a new evaluation. Proceed to Section 3.

### 3. Gather Design Context

Ask the founder:

**"What design/prototype are we evaluating today?"**

Prompt for:
- **Artifact type:** Wireframes, high-fidelity mockups, interactive prototype, live website
- **Scope:** Which screens/flows to evaluate (e.g., "landing page + signup flow" or "dashboard core features")
- **Access:** How to access the design (file reference, URL, description)
- **Stage:** Pre-implementation, post-implementation, pre-launch

**If no design exists:** HALT and say:
> "You need design artifacts to evaluate. Complete [U] User Flow & IA or [D] Design Direction in the M4 menu first, then return here."

### 4. Explain Heuristic Evaluation

Present this explanation:

---

**What is Heuristic Evaluation?**

Heuristic evaluation is a usability inspection method where we systematically examine your design against 10 established usability principles (Nielsen's heuristics). Think of it as a usability audit before user testing.

**Why do this now?**
- Catch obvious usability issues before showing to users
- Cheaper and faster to fix issues in design than after launch
- Complements (doesn't replace) user testing

**Nielsen's 10 Heuristics (we'll evaluate all 10):**
1. Visibility of system status (feedback, loading states)
2. Match between system and real world (familiar language)
3. User control and freedom (undo, cancel, exit)
4. Consistency and standards (predictable patterns)
5. Error prevention (constraints, confirmations)
6. Recognition rather than recall (visible options)
7. Flexibility and efficiency (shortcuts, bulk actions)
8. Aesthetic and minimalist design (focus, clarity)
9. Help users recover from errors (clear error messages)
10. Help and documentation (contextual help)

**Process:**
1. **Review:** Walk through each screen/flow, identify violations
2. **Rate:** Assign severity (0-4: cosmetic to catastrophic)
3. **Recommend:** Prioritize fixes by severity and effort
4. **Synthesize:** Update project-memo.md with findings

**Time investment:** 2-4 hours for a typical landing page or core flow.

---

### 5. Create Output Document

If this is a new evaluation, create `{outputFile}` with this structure:

```markdown
---
projectName: {from project-memo.md}
framework: heuristic-evaluation
milestone: m4-prototypation
stepsCompleted: []
evaluationScope: {screens/flows being evaluated}
evaluationDate: {current date}
---

# Heuristic Evaluation

## Evaluation Context

**Artifact Type:** {wireframes/prototype/live site}
**Scope:** {which screens/flows}
**Stage:** {pre-implementation/post-implementation/pre-launch}
**Evaluator:** {founder name}
**Date:** {current date}

---

## Violations by Heuristic

{Will be populated in Step 2}

---

## Severity Summary

{Will be populated in Step 3}

---

## Recommendations

{Will be populated in Step 4}

---

## Synthesis

{Will be populated in Step 5}
```

Update frontmatter: `stepsCompleted: ['step-01-init.md']`

### 6. Present Menu Options

**Select an Option:**
- **[C] Continue** — proceed to heuristic review

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:
1. Confirm output document is created and frontmatter is updated
2. Load `{nextStepFile}` and follow its instructions

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:** 
- Framework knowledge loaded
- Design context gathered (artifact type, scope, access)
- Output document created with proper frontmatter
- Founder understands heuristic evaluation process

❌ **FAILURE:** 
- Proceeding without design artifacts
- Skipping framework explanation
- Loading next step before [C] is selected
