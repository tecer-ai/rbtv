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

**If pitch_type = investor:**
You are The Investor planning the information architecture of a deck that VCs will spend 2 minutes 40 seconds on. The narrative is agreed — now make every slide earn its real estate.

**If pitch_type = client:**
You are The Buyer planning the information architecture of a deck that a procurement team will evaluate. The narrative is agreed — now make every slide earn its real estate. Remember: buyers are busy and skeptical. If a slide doesn't help them say yes, it helps them say no.

### Step-Specific Rules

- Load the pitch reference knowledge before structuring
- Structure must reflect the agreed narrative from Step 03
- Every slide has ONE idea and passes the glance test
- Data annotations from Step 04 inform what goes on each slide

**If pitch_type = investor:**
- Total deck: 12-15 slides

**If pitch_type = client:**
- Total deck: 10-12 slides
- ROI and proof slides should be early in the deck (buyers need conviction fast)

---

## MANDATORY SEQUENCE

### 1. Load Pitch Reference

**If pitch_type = investor:**
Read `{referenceFile}` completely. This is your decision-making guide for slide design and layout patterns.

**If pitch_type = client:**
Read `{referenceFile}` completely. Focus on the client pitch section.

### 2. Load Narrative

Read `{output_folder}/pitch-narrative.md`. This is the agreed story — the structure must serve it.

### 3. Map Narrative to Slide Specs

For each slide in the narrative, create the structural specification:

**If pitch_type = investor:**

| # | Slide Title (from narrative) | Layout Type | Key Visual Element | Data Points | Content Density |
|---|------------------------------|-------------|-------------------|-------------|-----------------|
| 1 | {title} | {e.g., hero, stats, comparison, diagram} | {what the eye should hit first} | {numbers/metrics on this slide} | {sparse/medium/dense} |

**If pitch_type = client:**

| # | Slide Title (from narrative) | Layout Type | Key Visual Element | Proof Points | Content Density |
|---|------------------------------|-------------|-------------------|-------------|-----------------|
| 1 | {title} | {e.g., hero, comparison, process, proof, CTA} | {what the eye should hit first} | {evidence on this slide} | {sparse/medium/dense} |

### 4. Identify Slide Patterns

Group slides by visual pattern to ensure consistency:

**If pitch_type = investor:**
- **Hero slides** (title, vision) — large text, minimal elements
- **Data slides** (traction, market, unit economics) — numbers as focal point
- **Comparison slides** (competition, before/after) — side-by-side or matrix
- **Story slides** (problem, solution) — icon + text, or image + text
- **Action slides** (the ask) — clear CTA with supporting detail

**If pitch_type = client:**
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
- **Data/Proof:** {any numbers/metrics/evidence, noting which need research}
- **Visual:** {image, icon, chart, or text-only}
```

**If pitch_type = investor:**
Ask the user:
- "Does this structure work? Would you like to:"
  - Add slides
  - Remove slides
  - Reorder slides
  - Change layout approaches
  - Adjust content density on any slide

**If pitch_type = client:**
Ask the user:
- "Does this structure work for {target_client}? Would you like to:"
  - Add slides
  - Remove slides
  - Reorder slides (e.g., move proof earlier)
  - Change layout approaches
  - Adjust content density

Wait for response. Apply adjustments.

### 6. Finalize Structure

Present the final slide plan with confirmed content and layout mapping. This becomes the blueprint for HTML generation.

### 7. Present Menu

**Select an Option:**
- **[C] Continue** — hand off to the design agent for HTML generation
- **[X] Exit** — exit workflow

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:

> **AGENT HANDOFF — Design Agent Required**
>
> Steps 07-08 (HTML generation and image prompts) are owned by the **design agent (Vivian)**, not the current narrative agent. You cannot execute these steps yourself.
>
> Instruct the user:
>
> *"The slide structure is locked. HTML generation and image work require the design agent. To continue, invoke Vivian using the command `@bmad-rbtv-designer` and select **[PD] Pitch Deck Design**. She'll pick up from the finalized structure."*
>
> Do NOT load `{nextStepFile}` yourself. The design agent will load it.

ONLY when **[X] Exit** is selected:
1. Confirm exit and end workflow

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:**
- Pitch reference loaded and applied
- Structure reflects the agreed narrative (not a generic template)
- Every slide has clear layout type and focal element
- User confirmed the structure

**If pitch_type = investor:**
- Total slides within 12-15 range

**If pitch_type = client:**
- Total slides within 10-12 range
- Proof slides positioned early enough to build conviction

❌ **FAILURE:**
- Proposing a generic structure that ignores the narrative
- Cramming multiple ideas on one slide
- Proceeding without user confirmation

**If pitch_type = investor:**
- Ignoring data layer annotations

**If pitch_type = client:**
- Burying proof slides late in the deck
