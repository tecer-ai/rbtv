---
name: 'step-01-init'
description: 'Load context, verify prerequisites, explain Brand Prism framework'
nextStepFile: './step-02-external-facets.md'
outputFile: '{outputFolder}/brand-prism.md'
---

# Step 1: Initialize Brand Prism

**Progress: Step 1 of 5** — Next: External Facets

---

## STEP GOAL

Verify Brand Archetypes prerequisite, load context from project-memo and prior frameworks, explain Kapferer's prism methodology.

---

## MANDATORY EXECUTION RULES

### Universal Rules
- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement
You are a YC mentor. The Brand Prism synthesizes all prior brand and customer work. Challenge incomplete or contradictory definitions. Demand evidence from upstream frameworks.

### Step-Specific Rules
- Brand Archetypes MUST be complete before starting Brand Prism
- If prerequisites missing, HALT and explain what's needed
- If brand-prism.md exists with stepsCompleted, offer to continue
- Do NOT define facets in this step — that's Steps 2-4

---

## CONTEXT TO LOAD

1. Read `{outputFolder}/project-memo.md` for project context and stepsCompleted
2. Read `./data/brand-prism-framework.md` for framework knowledge
3. Check prerequisites by verifying these exist in stepsCompleted:
   - `bi-m3-brand-archetypes` (REQUIRED)
   - `bi-m1-working-backwards`
   - `bi-m1-jobs-to-be-done`
   - `bi-m1-lean-canvas`
4. Read `{outputFolder}/brand-archetypes.md` for archetype personality and relationship
5. Check if `{outputFolder}/brand-prism.md` exists (continuation mode)

---

## MANDATORY SEQUENCE

### 1. Prerequisite Verification

Check project-memo stepsCompleted for:

**Required:**
- Brand Archetypes (personality, voice character, relationship type)

**Required M1 Frameworks:**
- Working Backwards (customer definition, tangible product)
- Jobs-to-be-Done (emotional jobs, social jobs)
- Lean Canvas (UVP, Customer Segments, Unfair Advantage)

If missing Brand Archetypes:
> "⛔ **Prerequisite Incomplete**
>
> Brand Prism requires Brand Archetypes to be complete.
> The Personality facet derives directly from your archetype selection.
>
> Complete Brand Archetypes first, then return here.
>
> Return to: bi-m3-brand-archetypes"

HALT — do not proceed.

### 2. Context Detection

If prerequisites met:
- Check for existing `brand-prism.md` with `stepsCompleted`
- If exists:
  - Display last completed step
  - Offer: "Continue from step N?" or "Start fresh?"
- If no existing output:
  - Proceed to framework introduction

### 3. Framework Introduction

Explain Brand Prism briefly:

> "Kapferer's Brand Identity Prism defines your brand through 6 interconnected facets:
>
> **Sender Side (Brand):**
> - Physique — tangible characteristics customers encounter
> - Personality — character traits (from your archetype)
> - Culture — values and beliefs driving the brand
>
> **Receiver Side (Customer):**
> - Reflection — how customers appear to others through you
> - Self-Image — how customers feel internally using you
>
> **Bridge:**
> - Relationship — the dynamic between brand and customer
>
> The prism synthesizes all your M1/M2/M3 work into a coherent identity system."

### 4. Prism Inputs Summary

From project-memo and prior frameworks, extract and present:

**From Brand Archetypes:**
- Primary archetype name and motivation
- Voice character adjectives (is/is not)
- Relationship type
- Visual style direction

**From JTBD:**
- Key emotional jobs (→ Self-Image)
- Key social jobs (→ Reflection)
- Forces (push, pull, anxieties, habits)

**From Working Backwards:**
- Customer narrative language
- PR headline and How It Works

**From Lean Canvas:**
- UVP statement
- Unfair Advantage
- Customer Segments

Present: "Here are the inputs that will populate your prism facets..."

### 5. Create Output Document

If not continuing, create brand-prism.md:

```yaml
---
name: brand-prism
project: '{project-name}'
stepsCompleted: ['step-01-init']
status: in-progress
---

# Brand Prism: {Project Name}

## Prism Inputs Summary

*(Compiled from Brand Archetypes, JTBD, Working Backwards, Lean Canvas)*

## Sender Facets

### Physique
*(To be completed in Step 2)*

### Personality
*(To be completed in Step 2)*

### Culture
*(To be completed in Step 2)*

## Receiver Facets

### Reflection
*(To be completed in Step 3)*

### Self-Image
*(To be completed in Step 3)*

## Bridge Facet

### Relationship
*(To be completed in Step 4)*

## Consistency Assessment

*(To be completed in Step 4)*

## Prism Narrative

*(To be completed in Step 4)*

## Integration Notes

*(To be completed in Step 5)*

## Synthesis

*(To be completed in Step 5)*
```

### 6. Present Menu Options

**Select an Option:**
- **[C] Continue** — proceed to External Facets (Physique, Personality, Culture)

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:
1. Ensure brand-prism.md exists with frontmatter
2. Verify `step-01-init` is in `stepsCompleted`
3. Load `./step-02-external-facets.md` and follow its instructions

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:** Prerequisites verified, prism inputs compiled, output document created

❌ **FAILURE:** Proceeding without Brand Archetypes, defining facets in this step, skipping inputs summary
