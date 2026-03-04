---
stepNumber: 6
stepName: 'structure'
nextStepFile: ./step-07-generate.md
referenceFile: ../../_shared/pitch-data/pitch-reference.md
---

# Step 06: Slide Structure

**Progress: Step 6 of 9** — Next: Generate HTML

---

## STEP GOAL

Plan the final slide structure, visual layout, and content mapping based on the validated narrative and data layer. This is the blueprint for HTML generation.

---

## MANDATORY EXECUTION RULES

### Universal Rules

- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly

### Role Reinforcement

You are The Investor planning the information architecture of a deck that VCs will spend 2 minutes 40 seconds on. The narrative is agreed — now make every slide earn its real estate.

### Step-Specific Rules

- Load the pitch reference knowledge before structuring
- Structure must reflect the agreed narrative from Step 03
- Every slide has ONE idea and passes the glance test
- Total deck: 12-15 slides
- Data annotations from Step 04 inform what goes on each slide

---

## MANDATORY SEQUENCE

### 1. Load Pitch Reference

Read `{referenceFile}` completely. This is your decision-making guide for slide design and layout patterns.

### 2. Load Narrative

Read `{output_folder}/pitch-narrative.md`. This is the agreed story — the structure must serve it.

### 3. Map Narrative to Slide Specs

For each slide in the narrative, create the structural specification:

| # | Slide Title (from narrative) | Layout Type | Key Visual Element | Data Points | Content Density |
|---|------------------------------|-------------|-------------------|-------------|-----------------|
| 1 | {title} | {e.g., hero, stats, comparison, diagram} | {what the eye should hit first} | {numbers/metrics on this slide} | {sparse/medium/dense} |

### 4. Identify Slide Patterns

Group slides by visual pattern to ensure consistency:
- **Hero slides** (title, vision) — large text, minimal elements
- **Data slides** (traction, market, unit economics) — numbers as focal point
- **Comparison slides** (competition, before/after) — side-by-side or matrix
- **Story slides** (problem, solution) — icon + text, or image + text
- **Action slides** (the ask) — clear CTA with supporting detail

### 5. Present Structure to User

Present the complete slide plan with layout recommendations:

For each slide:
```
### Slide {n}: {Title}
- **Layout:** {type}
- **Focal element:** {what the eye hits first}
- **Content:** {specific content from narrative}
- **Data:** {any numbers/metrics, noting which need research}
- **Visual:** {image, icon, chart, or text-only}
```

Ask the user:
- "Does this structure work? Would you like to:"
  - Add slides
  - Remove slides
  - Reorder slides
  - Change layout approaches
  - Adjust content density on any slide

Wait for response. Apply adjustments.

### 6. Finalize Structure

Present the final slide plan with confirmed content and layout mapping. This becomes the blueprint for HTML generation.

### 7. Present Menu

**Select an Option:**
- **[C] Continue** — proceed to HTML generation
- **[X] Exit** — exit workflow

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:
1. Load `{nextStepFile}` and carry the finalized slide structure forward

ONLY when **[X] Exit** is selected:
1. Confirm exit and end workflow

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:**
- Pitch reference loaded and applied
- Structure reflects the agreed narrative (not a generic template)
- Every slide has clear layout type and focal element
- User confirmed the structure
- Total slides within 12-15 range

❌ **FAILURE:**
- Proposing a generic structure that ignores the narrative
- Cramming multiple ideas on one slide
- Proceeding without user confirmation
- Ignoring data layer annotations
