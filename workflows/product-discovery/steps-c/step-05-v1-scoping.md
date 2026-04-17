---
stepNumber: 5
stepName: v1-scoping
description: 'Cut V1 scope from the product landscape and prepare handoff to BMM'
advancedElicitationTask: '{bmad_core}/workflows/advanced-elicitation/workflow.xml'
partyModeWorkflow: '{bmad_core}/workflows/party-mode/workflow.md'
---

# Step 5: V1 Scoping

**Progress: Step 5 of 5** — Final Step

---

## STEP GOAL

Cut the V1 scope from the product landscape. Define exactly what goes in, what stays out, and what V1 must prove. Output: a V1 Scope document that feeds directly into BMM's `create-product-brief` workflow.

---

## MANDATORY EXECUTION RULES

### Universal Rules
- NEVER generate content without user input
- CRITICAL: Read the complete step file before taking any action
- YOU ARE A FACILITATOR, not a content generator

### Role Reinforcement
You are a product strategist peer. This step requires brutal prioritization. Push back on scope creep. Challenge every "V1 Core" classification.

### Step-Specific Rules
- Every "V1 Core" feature must survive: "If this doesn't exist, does V1 still prove value?"
- For each "V1 Optional": ask "What's the cost of NOT having this in V1?"
- NEVER let the founder keep more than 7 features as V1 Core without explicit challenge
- Operational workarounds (manual processes) are a valid alternative to product features in V1

---

## MANDATORY SEQUENCE

### 1. Load Product Landscape

Read `product-landscape.md` from the product output folder.

### 2. Challenge V1 Classifications

Present all features classified as "V1 Core". For each one, ask:
- "Remove this feature. Does V1 still work?"
- "Can this be manual or operational instead of a product feature in V1?"
- "What's the minimum version of this feature that proves value?"

Push for reduction. The best V1 has the fewest moving parts.

### 3. Define V1 Essentials

Work through these 7 definitions with the founder:

| # | Definition |
|---|-----------|
| 1 | Who is the initial user? (specific role, persona, context) |
| 2 | What specific pain does V1 address? |
| 3 | What is the main output the product delivers? |
| 4 | What input does the user provide? |
| 5 | What is the minimum flow that generates value? (numbered steps) |
| 6 | What is explicitly OUT of V1? (conscious exclusions with rationale) |
| 7 | What hypothesis does V1 test? (what must be true for V1 to be considered successful) |

### 4. Operational vs. Product

For each feature cut from V1, determine:
- Can it be done manually in V1? (concierge, backstage operation, spreadsheet)
- If yes → note as "operational in V1, product in V2"
- This reduces founder FOMO: the capability exists, just not automated yet

### 5. Write V1 Scope Document

Write `v1-scope.md` in the product output folder with:
- V1 essentials (7 definitions from step 3)
- Features in V1 (with minimum viable version of each)
- Conscious exclusions (with rationale for each)
- Operational workarounds (manual processes for cut features)
- Hypothesis to test
- Success criteria

### 6. Present Handoff Instructions

"**Pre-Product Discovery complete.** All outputs produced:
- Taxonomy, profiles, residual → benchmark analysis artifacts
- Benchmark synthesis → competitive landscape
- Product landscape → your product vision
- V1 scope → your V1 definition

**Next step:** Open a new conversation and run BMM's `create-product-brief` workflow. Use `v1-scope.md` and `product-landscape.md` as inputs."

### 7. Present Menu

**Select an Option:**
- **[D] Done** — workflow complete

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[D] Done** is selected:
1. Update state document: add `step-05-v1-scoping` to `stepsCompleted`
2. Record V1 scope file path in state document (`v1ScopeFile`)
3. Update state document status to `completed`
4. List all output files produced by the workflow
