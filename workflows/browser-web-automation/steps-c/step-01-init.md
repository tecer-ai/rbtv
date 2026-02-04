---
stepNumber: 1
stepName: 'init'
nextStepFile: ./step-02-navigate.md
outputFile: '{output_folder}/browser-session-{slug}.md'
---

# Step 01: Init

**Progress: Step 1 of 4** — Next: Navigate

---

## STEP GOAL

Initialize the workflow, identify target URL(s), and determine operation mode.

---

## MANDATORY EXECUTION RULES

### Universal Rules

- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement

You are a Browser Automation Specialist. Precise, methodical, focused on reliable screenshot capture.

### Step-Specific Rules

- Confirm target URL(s) or file path(s)
- Determine operation mode (single capture, research, local file)
- Establish output location for screenshots

---

## MANDATORY SEQUENCE

### 1. Greet and Identify Target

Present brief introduction:

```
I'll help you with browser automation. I need:
1. Target URL(s) or local file path(s)
2. Operation mode (single capture, multi-site research, or local file view)
3. Viewport preference (desktop 1440×900 is default)
```

### 2. Confirm Target

If URL/path already in conversation context, confirm:
- "I see you want to navigate to [URL/path]. Is this correct?"

If no URL, ask:
- "What URL or file would you like me to navigate to?"

HALT and wait for confirmation or URL.

### 3. Determine Operation Mode

Present mode options:

```
Which operation mode?

[1] Single Capture — One website, full-page screenshot
[2] Research Mode — Multiple sites, comparative analysis
[3] Local File — Open local file in browser
[4] Interactive — Navigate and interact with page elements
```

HALT and wait for selection.

### 4. Establish Output Location

Default: `{output_folder}/screenshots/`

Ask if user wants custom location or use default.

### 5. Create Session Document

Initialize session document with frontmatter:

```yaml
---
title: 'Browser Session: {target-identifier}'
docType: 'browser-automation'
mode: '{capture|research|local|interactive}'
targets:
  - url: '{url}'
    status: 'pending'
viewport: '{width}×{height}'
outputFolder: '{output_folder}/screenshots/'
stepsCompleted: ['step-01-init.md']
date: '{current-date}'
---
```

### 6. Handle Local File Paths

If operation mode is Local File:

1. Get the absolute file path
2. Replace backslashes with forward slashes
3. Construct file URL: `file:///[absolute_path]`

Example:
- Path: `H:\repos\project\output\diagram.png`
- URL: `file:///H:/repos/project/output/diagram.png`

NEVER prepend `https://`. NEVER URL-encode the path.

### 7. Present Menu Options

**Select an Option:**

- **[C] Continue** — Proceed to navigation (step-02)
- **[X] Exit Workflow** — Save current state, exit

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:

1. Ensure frontmatter is updated with `step-01-init.md` in `stepsCompleted`
2. Load `./step-02-navigate.md` and follow its instructions

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:**
- Target URL(s) or path(s) confirmed
- Operation mode selected
- Output location established
- Session document created with valid frontmatter
- Menu presented with explicit HALT

❌ **FAILURE:**
- Proceeding without target confirmation
- Missing operation mode selection
- Proceeding to next step without user selecting Continue
