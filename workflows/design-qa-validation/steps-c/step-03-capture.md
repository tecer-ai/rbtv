---
stepNumber: 3
stepName: 'capture'
nextStepFile: ./step-04-analyze.md
---

# Step 03: Screenshot Capture

**Progress: Step 3 of 4** — Next: 4-Layer Analysis

---

## STEP GOAL

Capture visual screenshots at all required viewports for design validation analysis.

---

## MANDATORY EXECUTION RULES

### Universal Rules

- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement

You are a Design QA Specialist. Capture clean, accurate screenshots for analysis.

### Step-Specific Rules

- Use `browser_take_screenshot` for VISUAL screenshots (NEVER browser_snapshot)
- Capture at ALL required viewports for the document type
- Full-page screenshots when content scrolls
- Save with consistent naming convention
- Load ALL screenshots into context before analysis

---

## MANDATORY SEQUENCE

### 1. Determine Required Viewports

Based on document type from step-01:

| Type | Viewports |
|------|-----------|
| Website / Landing Page | 375×667, 768×1024, 1440×900 |
| Presentation | 1920×1080 |
| One-Pager | 375×667, 768×1024, 1920×1080 |
| Infographic | 1920×1080 |

Report: "Document type: {type}. Capturing at: {viewport-list}"

### 2. Capture Each Viewport

For EACH required viewport, execute:

1. **Lock browser** (if tab exists):
   - `browser_lock` to ensure exclusive access

2. **Navigate** (if not already on page):
   - `browser_navigate` to `http://localhost:{port}/{filename}`

3. **Resize viewport**:
   - `browser_resize` to target width × height

4. **Wait for load**:
   - `browser_wait_for` network idle or 2 seconds

5. **Capture screenshot**:
   - `browser_take_screenshot` with full_page: true
   - Save to `{filename}_screenshots/{viewport-name}.png`

6. **Unlock browser** when done with all captures:
   - `browser_unlock`

### 3. Viewport Naming Convention

| Viewport | Filename |
|----------|----------|
| 375×667 | mobile-375x667.png |
| 768×1024 | tablet-768x1024.png |
| 1440×900 | desktop-1440x900.png |
| 1920×1080 | fullhd-1920x1080.png |

### 4. Capture Interactive States (If Applicable)

For multi-page sites or interactive components:

- **Navigation states**: Hover over nav, capture
- **Modal states**: Trigger modal, capture
- **Dropdown states**: Open dropdowns, capture
- Naming: `{component}-{state}.png` (e.g., `nav-hover.png`, `modal-open.png`)

### 5. Load All Screenshots

Use `read_file` to load EACH screenshot into context:
- "Loading {filename} for analysis..."

Report: "Loaded {N} screenshots into context. Ready for analysis."

### 6. Check Console Errors

Use `browser_console_messages` to capture any JavaScript errors:
- Report errors found (if any)
- Document in output report

### 7. Update State

Add `step-03-capture.md` to `stepsCompleted` in output document frontmatter.

Update output document with screenshots section:
```markdown
## Screenshots Captured

| Viewport | File |
|----------|------|
| {viewport} | {filename} |
```

### 8. Present Menu Options

**Select an Option:**

- **[C] Continue** — Proceed to 4-layer analysis (step-04)
- **[R] Recapture** — Capture additional screenshots or retry
- **[X] Exit Workflow** — Save current state, exit

ALWAYS halt and wait for user selection.

---

## CRITICAL TOOL SELECTION

| Task | Correct Tool | Wrong Tool |
|------|--------------|------------|
| Visual screenshot | `browser_take_screenshot` | ~~browser_snapshot~~ |
| Page structure check | `browser_snapshot` | - |
| Console errors | `browser_console_messages` | - |

**browser_snapshot** returns accessibility tree (text), NOT visual image. NEVER use for design validation.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:

1. Ensure frontmatter is updated with `step-03-capture.md` in `stepsCompleted`
2. Ensure ALL screenshots are loaded into context
3. Load `./step-04-analyze.md` and follow its instructions

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:**
- All required viewports captured
- Screenshots saved with correct naming
- All screenshots loaded into context
- Console errors documented (if any)
- Frontmatter updated
- Menu presented with explicit HALT

❌ **FAILURE:**
- Missing viewports for document type
- Using browser_snapshot instead of browser_take_screenshot
- Proceeding to analysis without loading screenshots
- Proceeding to next step without user selecting Continue
