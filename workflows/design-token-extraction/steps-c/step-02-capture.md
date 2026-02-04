---
stepNumber: 2
stepName: 'capture'
nextStepFile: ./step-03-extract.md
playwrightSkill: '{project-root}/.cursor/skills/playwright-browser-automation/SKILL.md'
---

# Step 02: Screenshot Capture

**Progress: Step 2 of 4** — Next: Token Extraction

---

## STEP GOAL

Capture full-page screenshots at standard viewport sizes for design analysis.

---

## MANDATORY EXECUTION RULES

### Universal Rules

- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement

You are a Design System Analyst. Continue your methodical approach.

### Step-Specific Rules

- Capture at standard viewports (1440×900 for desktop)
- Full-page screenshots, not viewport-only
- Save screenshots to project directory
- Load screenshots into context for analysis

---

## MANDATORY SEQUENCE

### 1. Check Screenshot Status

If screenshots already exist in context (detected in step-01):
- "Screenshots already available. Ready to extract tokens."
- Skip to menu options.

If no screenshots, continue to capture.

### 2. Navigate to Target

Use Playwright MCP or browser automation:

1. Navigate to target URL from output document frontmatter
2. Wait for page load (network idle)
3. Handle any cookie consent or modals if present

### 3. Set Viewport

Configure viewport for desktop analysis:
- Width: 1440px
- Height: 900px (initial, full-page capture extends)

### 4. Capture Full-Page Screenshot

Execute full-page screenshot:
- Format: PNG
- Full page: true (captures entire scrollable area)
- Save to: `{output_folder}/screenshots/`
- Filename: `{website-slug}-desktop.png`

### 5. Load Screenshot

Read the captured screenshot into context using `read_file` tool.

Confirm screenshot is accessible:
- "Screenshot captured and loaded. Ready for token extraction."

### 6. Update State

Add `step-02-capture.md` to `stepsCompleted` in output document frontmatter.

### 7. Present Menu Options

**Select an Option:**

- **[C] Continue** — Proceed to token extraction (step-03)
- **[R] Recapture** — Capture screenshot again with different settings
- **[X] Exit Workflow** — Save current state, exit

ALWAYS halt and wait for user selection.

---

## VIEWPORT REFERENCE

| Device | Width | Height | Use Case |
|--------|-------|--------|----------|
| Desktop | 1440 | 900 | Primary analysis viewport |
| Tablet | 768 | 1024 | Responsive check |
| Mobile | 375 | 812 | Mobile patterns |

Default: Desktop only. User can request additional viewports.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:

1. Ensure frontmatter is updated with `step-02-capture.md` in `stepsCompleted`
2. Load `./step-03-extract.md` and follow its instructions

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:**
- Screenshot captured or pre-existing confirmed
- Screenshot loaded into context
- Frontmatter updated
- Menu presented with explicit HALT

❌ **FAILURE:**
- Attempting token extraction without screenshot in context
- Proceeding to next step without user selecting Continue
