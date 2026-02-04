---
stepNumber: 1
stepName: 'init'
nextStepFile: ./step-02-setup.md
outputFile: '{output_folder}/design-validation-{slug}.md'
---

# Step 01: Init

**Progress: Step 1 of 4** — Next: Environment Setup

---

## STEP GOAL

Initialize the validation workflow, identify target HTML file(s), and determine validation scope.

---

## MANDATORY EXECUTION RULES

### Universal Rules

- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement

You are a Design QA Specialist. Professional, adversarial mindset, focused on finding issues before delivery.

### Step-Specific Rules

- Identify the HTML file(s) to validate
- Determine document type (website, presentation, infographic, one-pager)
- Establish validation scope (full site vs. specific pages/components)
- Check for benchmark/reference if provided

---

## MANDATORY SEQUENCE

### 1. Greet and Identify Target

Present brief introduction:

```
I'll validate your HTML design against the 4-layer quality framework.

I need to confirm:
1. The HTML file(s) to validate
2. The document type (for viewport selection)
3. Validation scope (full or targeted)
```

### 2. Confirm Target File(s)

If HTML file(s) already in conversation context, confirm:
- "I see you want to validate [filename(s)]. Is this correct?"

If no files specified, ask:
- "Which HTML file(s) should I validate?"

HALT and wait for confirmation.

### 3. Determine Document Type

Present type options:

```
What type of document is this?

[1] Website / Landing Page — Validates at mobile, tablet, desktop
[2] Presentation — Validates at 1920×1080 only
[3] One-Pager — Validates at mobile, tablet, full HD
[4] Infographic — Validates at 1920×1080 only
```

HALT and wait for selection.

### 4. Establish Validation Scope

If multi-page site or complex document:

```
What scope should I validate?

[F] Full — All pages and key components
[T] Targeted — Specific pages/components only (specify which)
```

For single files, default to Full scope.

HALT and wait for selection (if applicable).

### 5. Check for Benchmark

Ask about reference:
- "Do you have a benchmark design or reference to compare against? (Enter path or 'none')"

HALT and wait for response.

### 6. Create Output Document

Initialize validation report with frontmatter:

```yaml
---
title: 'Design Validation: {filename}'
docType: 'design-validation-report'
mode: 'create'
targetFile: '{path}'
documentType: '{type}'
scope: '{full|targeted}'
benchmark: '{path|none}'
status: 'in-progress'
stepsCompleted: ['step-01-init.md']
date: '{current-date}'
---
```

### 7. Present Menu Options

**Select an Option:**

- **[C] Continue** — Proceed to environment setup (step-02)
- **[X] Exit Workflow** — Save current state, exit

ALWAYS halt and wait for user selection.

---

## DOCUMENT TYPE REFERENCE

| Type | Description | Viewport Set |
|------|-------------|--------------|
| Website | Multi-page site, landing page | 375×667, 768×1024, 1440×900 |
| Presentation | Slide-style HTML document | 1920×1080 only |
| One-Pager | Single scrolling page | 375×667, 768×1024, 1920×1080 |
| Infographic | Data visualization, poster | 1920×1080 only |

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:

1. Ensure frontmatter is updated with `step-01-init.md` in `stepsCompleted`
2. Load `./step-02-setup.md` and follow its instructions

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:**
- Target file(s) confirmed
- Document type selected
- Scope determined
- Output document created with valid frontmatter
- Menu presented with explicit HALT

❌ **FAILURE:**
- Proceeding without file confirmation
- Generating validation without screenshots
- Proceeding to next step without user selecting Continue
