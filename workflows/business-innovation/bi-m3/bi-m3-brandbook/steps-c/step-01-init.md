---
name: 'step-01-init'
description: 'Load all M3 contexts, verify prerequisites, set up AI image tool preference'
nextStepFile: './step-02-identity.md'
continueStepFile: './step-01b-continue.md'
outputFile: '{outputFolder}/brandbook.md'
---

# Step 1: Initialize Brandbook

**Progress: Step 1 of 5** — Next: Brand Identity

---

## STEP GOAL

Verify ALL 6 M3 frameworks are completed, load context from every framework output, explain the brandbook process, identify the founder's preferred AI image generation tool, and create the output document skeleton.

---

## Prior Context

**Builds on:** Brand Archetypes, Brand Prism, Golden Circle, Brand Positioning, Tone of Voice, Messaging Architecture
**Inherits (do not restate):** All M3 framework outputs — reference each framework's output file in `{outputFolder}/`
**This framework adds:** Consolidated brand identity (visual guidelines, compiled messaging, quick reference sheet)

---

## MANDATORY EXECUTION RULES

### Universal Rules
- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement
You are a YC mentor. The brandbook is the culmination of all M3 brand work — the bridge from strategy to execution. Every visual and verbal choice must trace back to the frameworks. Challenge any suggestion that contradicts established brand identity.

### Step-Specific Rules
- ALL 6 M3 frameworks must be complete before starting — no exceptions, no overrides
- If any framework is missing, HALT and redirect to M3 menu
- Do NOT create visual assets in this step — that is Step 3
- Do NOT compile sections in this step — that is Steps 2-4
- The founder's AI image tool preference must be recorded before proceeding

---

## CONTEXT TO LOAD

1. Read `{outputFolder}/project-memo.md` for project context and stepsCompleted
2. Read `./data/brandbook-framework.md` for framework knowledge
3. Verify ALL 6 M3 framework IDs exist in stepsCompleted:
   - `bi-m3-brand-archetypes`
   - `bi-m3-brand-prism`
   - `bi-m3-golden-circle`
   - `bi-m3-brand-positioning`
   - `bi-m3-messaging-architecture`
   - `bi-m3-tone-of-voice`
4. Check if `{outputFolder}/brandbook.md` exists (continuation mode)

---

## MANDATORY SEQUENCE

### 1. Prerequisite Verification

Check project-memo stepsCompleted for ALL 6 M3 framework IDs.

If ANY framework is missing:

> "⛔ **Prerequisites Incomplete**
>
> The Brandbook framework requires ALL 6 M3 brand frameworks to be completed first.
>
> Missing:
> - [List missing frameworks]
>
> The brandbook synthesizes every framework output. It cannot be built with incomplete inputs.
>
> Return to: M3 Brand milestone menu"

HALT — do not proceed. No override available.

### 2. Context Detection

If all prerequisites met:
- Check for existing `brandbook.md` with `stepsCompleted`
- If exists:
  - Display last completed step
  - Offer: "Continue from step N?" or "Start fresh?"
- If no existing output:
  - Proceed to framework summary

### 3. Load All Framework Outputs

Read and summarize key elements from each framework output:

| Framework | File | Key Elements to Extract |
|-----------|------|------------------------|
| Brand Archetypes | `{outputFolder}/brand-archetypes.md` | Primary archetype, IS/NOT traits, voice tendencies |
| Brand Prism | `{outputFolder}/brand-prism.md` | All 6 facets (physique, personality, culture, relationship, reflection, self-image) |
| Golden Circle | `{outputFolder}/golden-circle.md` | Why, How, What statements |
| Brand Positioning | `{outputFolder}/brand-positioning.md` | Positioning statement, perceptual map dimensions |
| Messaging Architecture | `{outputFolder}/messaging-architecture.md` | Brand promise, key messages, tagline candidates |
| Tone of Voice | `{outputFolder}/tone-of-voice.md` | Dimensions, voice summary, do/don't patterns |

Present consolidated summary:

> "Here's the brand identity foundation we'll compile into your brandbook:
>
> **Who:** [Archetype] personality with [Prism personality traits]
> **Why:** [Golden Circle Why]
> **Position:** [Positioning statement — abbreviated]
> **Promise:** [Brand promise from Messaging Architecture]
> **Voice:** [Voice summary from Tone of Voice]
>
> The brandbook will consolidate all of this and add visual identity (logo, colors, typography, imagery, icons) to create your complete brand reference."

### 4. Explain Brandbook Process

> "We'll build your brandbook in 4 remaining steps:
>
> 1. **Brand Identity** — Compile mission, vision, persona, audience, and values from your frameworks
> 2. **Visual Guidelines** — Define logo, color palette, typography, imagery style, and iconography. We'll generate AI prompts for logo and imagery creation.
> 3. **Messaging & Tone** — Compile voice, tone, tagline, value proposition, and key messaging. Build a quick reference sheet.
> 4. **Synthesis** — Validate consistency, compile the final document, and mark M3 Brand as complete.
>
> For visual assets (logos, imagery examples), I'll create prompts optimized for your preferred AI image generation tool. You'll generate the images, and we'll iterate until you're happy with the results."

### 5. AI Image Tool Selection

Ask the founder:

> "Which AI image generation tool do you prefer? I'll tailor all image prompts for that specific platform/model.
>
> Common options:
> - Google Gemini (Nano Banana) — multi-image fusion, identity locking
> - OpenAI (DALL-E / GPT Images) — conversational refinement
> - Midjourney — artistic styles, high fidelity
> - Other (please specify)
>
> I'll load platform-specific knowledge to optimize prompts for your tool."

Record the selection. Check if model/platform knowledge exists in the prompting knowledge index:
- Read `{rbtv_path}/workflows/ai-consulting/prompting-assistance/data/knowledge-index.csv`
- Search for matching `ai_model` or `platform` entries
- If found: note the knowledge file paths for Step 3
- If not found: inform the founder that generic image prompts will be generated, or suggest adding platform knowledge via DomCobb's [AK] Add Knowledge workflow

Update project-memo.md frontmatter with:
```yaml
preferredImageTool: '{selected tool}'
imageModelKnowledge: '{knowledge file path or "generic"}'
```

### 6. Create Output Document

If not continuing, create brandbook.md:

```yaml
---
name: brandbook
project: '{project-name}'
stepsCompleted: ['step-01-init']
status: in-progress
preferredImageTool: '{selected tool}'
---

# Brandbook: {Project Name}

## Brand Identity

*(To be completed in Step 2)*

## Visual Guidelines

### Logo

*(To be completed in Step 3)*

### Color Palette

*(To be completed in Step 3)*

### Typography

*(To be completed in Step 3)*

### Imagery & Photography

*(To be completed in Step 3)*

### Iconography

*(To be completed in Step 3)*

## Messaging & Tone

*(To be completed in Step 4)*

## Quick Reference Sheet

*(To be completed in Step 4)*

## Synthesis

*(To be completed in Step 5)*
```

### 7. Present Menu Options

**Select an Option:**
- **[C] Continue** — proceed to Brand Identity compilation

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:
1. Ensure brandbook.md exists with frontmatter
2. Verify `step-01-init` is in `stepsCompleted`
3. Verify AI image tool preference is recorded
4. Load `./step-02-identity.md` and follow its instructions

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:** All 6 M3 prerequisites verified, all framework outputs loaded and summarized, AI image tool selected and recorded in project-memo, output document created

❌ **FAILURE:** Proceeding with missing frameworks, skipping AI tool selection, compiling brand sections in this step, generating image prompts in this step
