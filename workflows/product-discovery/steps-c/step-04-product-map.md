---
stepNumber: 4
stepName: product-map
description: 'Build the founder''s product vision through provocative elicitation, not benchmark copying'
nextStepFile: './step-05-v1-scoping.md'
advancedElicitationTask: '{bmad_core}/workflows/advanced-elicitation/workflow.xml'
partyModeWorkflow: '{bmad_core}/workflows/party-mode/workflow.md'
---

# Step 4: Product Map

**Progress: Step 4 of 5** — Next: V1 Scoping

---

## STEP GOAL

Build the founder's product vision — NOT by copying benchmarks, but by extracting what the founder believes the product must be. The benchmark synthesis provides context; the founder provides vision. Output: a Product Landscape with modules, features, and strategic classifications.

---

## MANDATORY EXECUTION RULES

### Universal Rules
- NEVER generate content without user input
- CRITICAL: Read the complete step file before taking any action
- YOU ARE A FACILITATOR, not a content generator

### Role Reinforcement
You are a product strategist peer. This is the most interactive step — provoke thinking, challenge assumptions, surface trade-offs. Push back when the founder copies benchmarks instead of thinking from first principles.

### Step-Specific Rules
- NEVER copy the benchmark taxonomy as the product map — the founder's product may organize differently
- ALWAYS challenge: "Is this because benchmarks have it, or because your user needs it?"
- For EVERY module the founder proposes, ask WHY it exists and whether the product works without it
- The product map is the founder's vision, not a benchmark summary

---

## MANDATORY SEQUENCE

### 1. Load Synthesis

Read `benchmark-synthesis.md` from the output folder. This is the only reference document for this step.

### 2. Vision Elicitation

Ask the founder these questions, one at a time. Do NOT proceed until each is answered:

1. "Forget the benchmarks for a moment. In your own words: what does your product DO? What's the core action?"
2. "Who is the primary user? What's their job title, their daily pain?"
3. "What's the single output that makes the user say 'this was worth it'?"

### 3. Module Discovery

Based on the founder's answers, propose an initial module list:

"Based on what you described, I see these potential modules: {list}."

For EACH module, ask:
- "Why does this module exist?"
- "Without this module, does the product still deliver value?"
- "Is this core to the value proposition, an enabler, or a future differentiator?"

The founder adds, removes, renames, reclassifies. Iterate until stable.

### 4. Feature Mapping

For each approved module, work through features:
- What features from the benchmarks are relevant here? (reference synthesis, not raw benchmarks)
- What features does the founder want that NO benchmark has?
- What benchmark features does the founder explicitly NOT want? Why?

### 5. Strategic Classification

For every feature, the founder classifies:

| Classification | Meaning |
|---------------|---------|
| **V1 Core** | Must exist in first version |
| **V1 Optional** | Nice to have in V1, can cut if needed |
| **Later** | Planned but not V1 |
| **Maybe Never** | Captured for completeness, unlikely to build |

### 6. Write Product Landscape

Write `product-landscape.md` in the product output folder with:
- Product vision summary (from step 2)
- Module map with rationale for each module
- Feature matrix with strategic classifications
- Conscious omissions (benchmark features explicitly rejected, with rationale)
- Open questions

### 7. Present Menu

**Select an Option:**
- **[C] Continue** — proceed to V1 Scoping

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:
1. Update state document: add `step-04-product-map` to `stepsCompleted`
2. Record product landscape file path in state document (`productMapFile`)
3. Load `{nextStepFile}` and follow its instructions
