---
stepNumber: 3
stepName: comparative-synthesis
description: 'Cross-reference all profiles into a concise comparative synthesis document'
nextStepFile: './step-04-product-map.md'
advancedElicitationTask: '{bmad_core}/workflows/advanced-elicitation/workflow.xml'
partyModeWorkflow: '{bmad_core}/workflows/party-mode/workflow.md'
---

# Step 3: Comparative Synthesis

**Progress: Step 3 of 5** — Next: Product Map

---

## STEP GOAL

Cross-reference all processed profiles into a concise comparative synthesis: which competitors have which capabilities, where patterns emerge, where gaps exist. The synthesis MUST be compact enough to fit in context for Step 4 — if it exceeds 200 lines, it failed.

---

## MANDATORY EXECUTION RULES

### Universal Rules
- NEVER generate content without user input
- CRITICAL: Read the complete step file before taking any action
- YOU ARE A FACILITATOR, not a content generator

### Role Reinforcement
You are a product strategist peer. Focus on patterns and gaps, not exhaustive feature lists.

### Step-Specific Rules
- The synthesis MUST stay under 200 lines — compress, do not expand
- Focus on product-relevant patterns, not company descriptions
- Always surface: what ALL competitors have, what FEW have, what NONE have
- Load all profiles directly — they are compact enough to fit in context

---

## MANDATORY SEQUENCE

### 1. Load All Profiles

Read the state document to get the profile folder path and list of processed benchmarks. Load all profile files.

### 2. Build Comparison Matrix

Create a table: rows = taxonomy modules/features, columns = competitors.

Mark each cell: **✓** (present), **○** (partial), **✗** (absent).

Present the matrix to the founder.

### 3. Extract Patterns

Analyze the matrix and present findings in these categories:

| Category | Definition |
|----------|------------|
| **Table Stakes** | Features present in 80%+ of competitors — minimum expectations |
| **Differentiators** | Features present in fewer than 30% — potential competitive advantages |
| **Gaps** | Features absent from ALL competitors — potential blue ocean |
| **Overcrowded** | Areas where all compete heavily — hard to differentiate on |
| **Emerging** | Features appearing only in newer/smaller competitors — possible trends |

### 4. Founder Discussion

Ask provocative questions:
- "Which patterns surprise you?"
- "Which gaps are real opportunities vs. things nobody wants?"
- "Where do you want to compete on execution (table stakes) vs. differentiation?"
- "Any findings from `residual.md` that now seem more important in light of the full picture?"

### 5. Write Synthesis Document

Write `benchmark-synthesis.md` in the structured output folder with:
- Comparison matrix (table)
- Pattern analysis (5 categories)
- Founder's key reactions and initial positions

Verify the document is under 200 lines. If over, compress further.

### 6. Present Menu

**Select an Option:**
- **[C] Continue** — proceed to Product Map

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:
1. Update state document: add `step-03-comparative-synthesis` to `stepsCompleted`
2. Record synthesis file path in state document (`synthesisFile`)
3. Load `{nextStepFile}` and follow its instructions
