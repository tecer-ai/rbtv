---
name: 'step-04-messaging'
description: 'Compile Messaging & Tone section, craft tagline, build quick reference sheet'
nextStepFile: './step-05-synthesis.md'
outputFile: '{outputFolder}/brandbook.md'
advancedElicitationTask: '{bmad_core}/workflows/advanced-elicitation/workflow.xml'
partyModeWorkflow: '{bmad_core}/workflows/party-mode/workflow.md'
---

# Step 4: Messaging & Tone

**Progress: Step 4 of 5** — Next: Synthesis

---

## STEP GOAL

Compile the Messaging & Tone section by synthesizing Tone of Voice and Messaging Architecture outputs, craft a tagline from the brand promise, define the value proposition, and build a one-page quick reference sheet.

---

## MANDATORY EXECUTION RULES

### Universal Rules
- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement
You are a YC mentor. The messaging section translates brand strategy into actionable communication guidelines. Every word must be backed by framework output. The tagline must distill the brand promise — not replace it. The quick reference sheet is the most-used page of the entire brandbook.

### Step-Specific Rules
- Tagline must derive from the brand promise (Messaging Architecture) — not be invented from scratch
- Value proposition must align with Lean Canvas UVP and Brand Positioning
- Quick reference sheet must fit on one page (concise, scannable)
- The founder approves the tagline before it is finalized

---

## CONTEXT TO LOAD

1. Read `{outputFolder}/brandbook.md` (current state)
2. Read `{outputFolder}/tone-of-voice.md` for voice dimensions, summary, do/don't
3. Read `{outputFolder}/messaging-architecture.md` for brand promise, key messages, audience cards
4. Read `{outputFolder}/brand-positioning.md` for positioning statement
5. Read `{outputFolder}/project-memo.md` for Lean Canvas UVP (M1)

---

## MANDATORY SEQUENCE

### 1. Brand Voice

Compile from Tone of Voice:

```markdown
### Brand Voice

{Voice summary from Tone of Voice — 2-3 sentences describing how the brand sounds}

#### Voice Dimensions

| Dimension | Position | Description |
|-----------|----------|-------------|
| {Dim 1} | {N}/5 | {Brief description of where brand sits on spectrum} |
| {Dim 2} | {N}/5 | {Brief description} |
| {Dim 3} | {N}/5 | {Brief description} |

*Source: Tone of Voice Framework*
```

### 2. Tone Guidelines

Compile from Tone of Voice do/don't and context adjustments:

```markdown
### Tone Guidelines

#### Do's and Don'ts

| Dimension | DO | DON'T |
|-----------|-----|-------|
| {Dim 1} | {Do example} | {Don't example} |
| {Dim 2} | {Do example} | {Don't example} |
| {Dim 3} | {Do example} | {Don't example} |

#### Context Adjustments

| Context | Tone Shift |
|---------|------------|
| Marketing | {How tone adjusts} |
| Onboarding | {How tone adjusts} |
| Support / Error | {How tone adjusts} |
| Documentation | {How tone adjusts} |
| Social Media | {How tone adjusts} |

*Source: Tone of Voice Framework — Do/Don'ts and Context Adjustments*
```

### 3. Tagline

Craft from brand promise (Messaging Architecture):

> "Your brand promise is: '{brand promise}'
>
> A tagline distills this into a short, memorable phrase (typically 3-7 words). It is NOT a slogan for a campaign — it is the enduring verbal signature of your brand.
>
> Here are 3 options derived from your promise:"

Present 3 tagline candidates. For each:
- State the tagline
- Explain which part of the brand promise it captures
- Note how it connects to the archetype voice

Ask founder to select, modify, or request new options. Iterate until approved.

```markdown
### Tagline

> "{Approved tagline}"

**Rationale:** Derived from brand promise "{brand promise}". Captures {what it emphasizes}.

*Source: Derived from Messaging Architecture — Brand Promise*
```

### 4. Value Proposition

Compile from Lean Canvas UVP and Brand Positioning:

```markdown
### Value Proposition

{Clear statement explaining the benefit of the product/service — synthesized from Lean Canvas UVP and Brand Positioning statement}

**For** {target audience} **who** {need/job-to-be-done},
**{Brand}** is the {category} **that** {key benefit},
**unlike** {alternative} **which** {limitation}.

*Source: Brand Positioning Statement, M1 Lean Canvas — UVP*
```

### 5. Key Messaging Summary

Compile from Messaging Architecture — distilled for the brandbook:

```markdown
### Key Messaging

**Brand Promise:** "{Brand promise}"

#### Messages by Audience

| Audience | Core Message |
|----------|-------------|
| Early Adopters | {Top message} |
| Mainstream | {Top message} |
| Partners | {Top message} |
| Investors | {Top message} |

For full messaging hierarchy (proof points, CTAs, audience cards), reference the complete Messaging Architecture document.

*Source: Messaging Architecture Framework*
```

### 6. Quick Reference Sheet

Compile a one-page summary:

```markdown
## Quick Reference Sheet

### Visual Identity

| Element | Reference |
|---------|-----------|
| Primary Logo | `brandbook-assets/logo-primary.png` |
| Secondary Logo | `brandbook-assets/logo-secondary.png` |
| Monochromatic Logo | `brandbook-assets/logo-mono.png` |

| Primary Colors | |
|---------------|---|
| {Color 1} | `#{hex}` |
| {Color 2} | `#{hex}` |

| Secondary Colors | |
|-----------------|---|
| {Color 1} | `#{hex}` |
| {Color 2} | `#{hex}` |

| Typography | |
|-----------|---|
| Headings | {Primary typeface}, Bold |
| Body | {Secondary typeface}, Regular |

### Verbal Identity

| Element | Content |
|---------|---------|
| Tagline | "{Tagline}" |
| Brand Promise | "{Brand promise}" |
| Voice Summary | {1 sentence} |
| Non-Negotiable Tone | {Core dimension that never shifts} |

### Core Rules

**Always:**
- {Top 3 brand do's}

**Never:**
- {Top 3 brand don'ts}
```

### 7. Compile Messaging & Tone Section

After founder approves all subsections, update brandbook.md:

Replace the `## Messaging & Tone` and `## Quick Reference Sheet` placeholders with the compiled content.

Update frontmatter:
```yaml
stepsCompleted: ['step-01-init', 'step-02-identity', 'step-03-visual', 'step-04-messaging']
```

### 8. Present Menu Options

**Select an Option:**
- **[C] Continue** — proceed to Synthesis

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:
1. Verify Messaging & Tone and Quick Reference sections are written to brandbook.md
2. Verify tagline is approved by founder
3. Verify `step-04-messaging` is in `stepsCompleted`
4. Load `./step-05-synthesis.md` and follow its instructions

- Ask which element to refine
- After refinement, redisplay menu

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:** Brand voice compiled from Tone of Voice, tone guidelines with do/don'ts and context adjustments documented, tagline crafted and approved by founder, value proposition aligned with positioning, key messaging summarized, quick reference sheet built as one-page scannable summary

❌ **FAILURE:** Inventing tagline without deriving from brand promise, skipping founder approval on tagline, missing source citations, quick reference too long for one page
