---
stepNumber: 3
stepName: 'structure'
nextStepFile: ./step-04-generate.md
referenceFile: ../data/pitch-reference.md
---

# Step 03: Slide Structure

**Progress: Step 3 of 6** — Next: Generate HTML

---

## STEP GOAL

Plan the slide structure, order, and content mapping based on pitch type, gathered content, and best practices.

---

## MANDATORY EXECUTION RULES

### Universal Rules

- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly

### Role Reinforcement

You are a Pitch Deck Architect planning the information architecture of a deck that investors will spend 2 minutes 40 seconds on. Every slide earns its right to exist.

### Step-Specific Rules

- Load the pitch reference knowledge before structuring
- Structure must match pitch type (investor vs client)
- Every slide has ONE idea and passes the glance test
- Total deck: 12-15 slides for investor, 10-12 for client

---

## MANDATORY SEQUENCE

### 1. Load Pitch Reference

Read `{referenceFile}` completely. This is your decision-making guide for slide selection and order.

### 2. Select Slide Template

Based on {pitch_type}, propose the appropriate structure:

**INVESTOR PITCH (12-15 slides):**

| # | Slide | Content Source | Purpose |
|---|-------|---------------|---------|
| 1 | Title / Company Purpose | Brand + Project Memo | Name + one-line description |
| 2 | Problem (Data) | M1 Problem + Context research | Who hurts, how much (numbers) |
| 3 | Problem (Human) | M1 Jobs-to-be-Done | Real situations, current workarounds |
| 4 | Solution | M1 Solution + Value Prop | What you do, concrete benefits |
| 5 | Before / After | M1 Problem-Solution Fit | Visual contrast of old vs new world |
| 6 | Why Now | Context research | Market/tech/regulatory tailwinds |
| 7 | Traction | M2 + Project Memo | Revenue, users, proof points |
| 8 | Market Size | M2 TAM/SAM/SOM | Bottom-up methodology |
| 9 | Competition | M1 Competitive Landscape | 2-axis quadrant, differentiation |
| 10 | Business Model | M2 Unit Economics | Who pays, how much, margins |
| 11 | Team | Project Memo / User input | Founders + unique qualifications |
| 12 | The Ask | User input | Amount, use of funds, milestones |
| 13 | Vision (optional) | Brand + User input | 10-word world domination line |

**CLIENT PITCH (10-12 slides):**

| # | Slide | Content Source | Purpose |
|---|-------|---------------|---------|
| 1 | Title | Brand | Company + tagline |
| 2 | Their Problem | M1 Problem + Context | Client's specific pain points |
| 3 | Current Reality | M1 Jobs-to-be-Done | How they're solving it today (poorly) |
| 4 | Our Solution | M1 Solution | What you do for them |
| 5 | How It Works | M1 Value Prop | Step-by-step or workflow |
| 6 | Before / After | M1 Problem-Solution Fit | Concrete transformation |
| 7 | Proof Points | M2 + Context | Case studies, metrics, testimonials |
| 8 | Why Us | M1 Competitive + M3 Brand | Differentiators, trust signals |
| 9 | Pricing | M2 Unit Economics | Plans, ROI framing |
| 10 | Next Steps | User input | CTA, timeline, contact |

### 3. Map Content to Slides

For each proposed slide, map the specific content from the pitch brief (or from standalone discovery):
- Show what content goes on each slide
- Identify slides that are content-rich vs. content-sparse
- Flag any slides where content is missing or weak

Present the complete mapping to the user.

### 4. User Review and Adjust

Ask the user:
- "Does this structure work? Would you like to:"
  - Add slides (e.g., product demo, go-to-market)
  - Remove slides
  - Reorder slides
  - Adjust content mapping for any slide

Wait for response. Apply adjustments.

### 5. Finalize Structure

Present the final slide plan with confirmed content mapping. This becomes the blueprint for HTML generation.

### 6. Present Menu

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
- Structure matches pitch type
- Every slide has clear, specific content mapped
- User confirmed the structure
- Total slides within 10-15 range

❌ **FAILURE:**
- Proposing slides without reference to best practices
- Cramming multiple ideas on one slide
- Structure doesn't match pitch type
- Proceeding without user confirmation
