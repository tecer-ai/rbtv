---
stepNumber: 1
stepName: 'init'
nextStepFile: ./step-02-discover.md
continueStepFile: './step-01b-continue.md'
outputFile: '{output_folder}/design-extraction-{slug}.md'
---

# Step 01: Init

**Progress: Step 1 of 5** — Next: Site Discovery

---

## STEP GOAL

Initialize the workflow, identify the target website, and determine output format preferences.

---

## MANDATORY EXECUTION RULES

### Universal Rules

- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement

You are a Design System Analyst. Professional, methodical, focused on extracting actionable design tokens from live websites.

### Step-Specific Rules

- Confirm the target website URL
- Determine output format preference (brief vs. tokens)
- The workflow will navigate the live site in step-02 — no screenshots needed yet

---

## MANDATORY SEQUENCE

### 1. Greet and Identify Target

Present brief introduction:

```
I'll help you extract design tokens from a live website. I'll navigate the site,
capture multiple pages, and extract tokens from both the DOM/CSS and visual analysis.

I need:
1. The target website URL
2. Your preferred output format
```

### 2. Confirm Target Website

If URL already in conversation context, confirm:
- "I see you want to analyze [URL]. Is this correct?"

If no URL, ask:
- "What website would you like me to analyze?"

HALT and wait for confirmation or URL.

### 3. Determine Output Format

Present format options:

```
Which output format do you need?

[1] Design Brief — Narrative prose with creative interpretation
[2] Design Tokens — Structured JSON with concrete values
[3] Both — Generate both formats
```

HALT and wait for selection.

### 4. Create Output Document

Initialize output document with frontmatter:

```yaml
---
title: 'Design Extraction: {website-name}'
docType: 'design-extraction'
mode: 'create'
targetUrl: '{url}'
outputFormat: '{brief|tokens|both}'
stepsCompleted: ['step-01-init.md']
date: '{current-date}'
---
```

### 5. Present Menu Options

**Select an Option:**

- **[C] Continue** — Proceed to site discovery (step-02)
- **[X] Exit Workflow** — Save current state, exit

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:

1. Ensure frontmatter is updated with `step-01-init.md` in `stepsCompleted`
2. Load `./step-02-discover.md` and follow its instructions

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:**
- Target URL confirmed
- Output format selected
- Output document created with valid frontmatter
- Menu presented with explicit HALT

❌ **FAILURE:**
- Proceeding without URL confirmation
- Proceeding to next step without user selecting Continue
