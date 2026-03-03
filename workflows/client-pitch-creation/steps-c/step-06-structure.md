---
stepNumber: 6
stepName: 'structure'
nextStepFile: ./step-07-generate.md
referenceFile: ../data/pitch-reference.md
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

You are The Buyer planning the information architecture of a deck that a procurement team will evaluate. The narrative is agreed — now make every slide earn its real estate. Remember: buyers are busy and skeptical. If a slide doesn't help them say yes, it helps them say no.

### Step-Specific Rules

- Load the pitch reference knowledge before structuring
- Structure must reflect the agreed narrative from Step 03
- Every slide has ONE idea and passes the glance test
- Total deck: 10-12 slides
- Data annotations from Step 04 inform what goes on each slide
- ROI and proof slides should be early in the deck (buyers need conviction fast)

---

## MANDATORY SEQUENCE

### 1. Load Pitch Reference

Read `{referenceFile}` completely. Focus on the client pitch section.

### 2. Load Narrative

Read `{output_folder}/pitch-narrative.md`. This is the agreed story — the structure must serve it.

### 3. Map Narrative to Slide Specs

For each slide in the narrative, create the structural specification:

| # | Slide Title (from narrative) | Layout Type | Key Visual Element | Proof Points | Content Density |
|---|------------------------------|-------------|-------------------|-------------|-----------------|
| 1 | {title} | {e.g., hero, comparison, process, proof, CTA} | {what the eye should hit first} | {evidence on this slide} | {sparse/medium/dense} |

### 4. Identify Slide Patterns

Group slides by visual pattern:
- **Hero slides** (title, next steps) — clean, confident, minimal
- **Problem slides** (their pain, current reality) — empathy-driven, data-supported
- **Solution slides** (what changes, how it works) — process diagrams, before/after
- **Proof slides** (case studies, ROI, testimonials) — numbers as focal point, trust signals
- **Comparison slides** (vs. alternatives) — honest, side-by-side
- **Action slides** (pricing, next steps) — clear CTA, remove friction

### 5. Present Structure to User

Present the complete slide plan with layout recommendations:

For each slide:
```
### Slide {n}: {Title}
- **Layout:** {type}
- **Focal element:** {what the eye hits first}
- **Content:** {specific content from narrative}
- **Proof:** {any evidence, noting which needs research}
- **Visual:** {image, icon, chart, process diagram, or text-only}
```

Ask the user:
- "Does this structure work for {target_client}? Would you like to:"
  - Add slides
  - Remove slides
  - Reorder slides (e.g., move proof earlier)
  - Change layout approaches
  - Adjust content density

Wait for response. Apply adjustments.

### 6. Finalize Structure

Present the final slide plan. This becomes the blueprint for HTML generation.

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
- Pitch reference loaded and client section applied
- Structure reflects the agreed narrative
- Proof slides positioned early enough to build conviction
- Every slide has clear layout type and focal element
- User confirmed the structure
- Total slides within 10-12 range

❌ **FAILURE:**
- Proposing a generic structure that ignores the narrative
- Burying proof slides late in the deck
- Cramming multiple ideas on one slide
- Proceeding without user confirmation
