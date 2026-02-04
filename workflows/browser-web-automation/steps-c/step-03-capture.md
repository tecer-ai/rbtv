---
stepNumber: 3
stepName: 'capture'
nextStepFile: ./step-04-finalize.md
---

# Step 03: Capture

**Progress: Step 3 of 4** — Next: Finalize

---

## STEP GOAL

Resize viewport, capture full-page screenshot(s), and copy to project directory.

---

## MANDATORY EXECUTION RULES

### Universal Rules

- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement

You are a Browser Automation Specialist. Precise screenshot capture is your focus.

### Step-Specific Rules

- Resize viewport before capture for consistency
- Full-page screenshots unless user specifies viewport-only
- MUST copy screenshots from temp to project directory
- Verify screenshots are accessible via `read_file`

---

## MANDATORY SEQUENCE

### 1. Resize Viewport

Set viewport to requested size (default: 1440×900):

```
mcp_cursor-ide-browser_browser_resize
width: 1440
height: 900
```

### 2. Wait for Resize Stabilization

Brief wait after resize:

```
mcp_cursor-ide-browser_browser_wait_for
timeout: 1000
```

### 3. Capture Full-Page Screenshot

Execute screenshot capture:

```
mcp_cursor-ide-browser_browser_take_screenshot
fullPage: true
type: "png"
```

Note: Screenshot returns temporary file path.

### 4. Copy to Project Directory

Browser MCP saves to temp directory — MUST copy to project:

1. Create target directory if needed: `{output_folder}/screenshots/`
2. Generate filename: `{site-slug}-{viewport}-{timestamp}.png`
3. Copy from temp path to project path
4. Verify file exists

Example directory structure:
```
{output_folder}/screenshots/{site-identifier}/desktop-1440x900.png
```

### 5. Load Screenshot for Verification

Read the copied screenshot to verify accessibility:

```
read_file: {project_screenshot_path}
```

Confirm screenshot loaded successfully.

### 6. Capture Additional Viewports (if requested)

If user requested multiple viewports, repeat steps 1-5 for each:

| Viewport | Width | Height | Filename Suffix |
|----------|-------|--------|-----------------|
| Desktop | 1440 | 900 | desktop-1440x900 |
| Tablet | 768 | 1024 | tablet-768x1024 |
| Mobile | 375 | 812 | mobile-375x812 |

### 7. Report Capture Results

```
Screenshots captured successfully:
- {filename1}: {width}×{height}
- {filename2}: {width}×{height}

Saved to: {output_folder}/screenshots/
```

### 8. Update State

Add `step-03-capture.md` to `stepsCompleted` in session document frontmatter.

Update target status from `navigated` to `captured`.

### 9. Present Menu Options

**Select an Option:**

- **[C] Continue** — Proceed to finalize (step-04)
- **[A] Additional Viewport** — Capture another viewport size
- **[R] Recapture** — Retake screenshot with different settings
- **[X] Exit Workflow** — Save current state, exit

ALWAYS halt and wait for user selection.

---

## NAMING CONVENTIONS

### Design Inspiration
- Pattern: `{site-identifier}/{viewport}.png`
- Site identifier: Domain name or descriptive name (stripe, linear, notion)
- Include viewport size in filename

### Local File Validation
- Pattern: `{file-name}_rendered.png`
- Example: `diagram_01_rendered.png`

---

## TROUBLESHOOTING

### Screenshot Not Found

If screenshot path invalid:
1. Verify temp path from tool output
2. Check file exists at temp location
3. Ensure target directory created
4. Use absolute paths for copy operation

### Incomplete Screenshot

If screenshot captures partial content:
1. Increase wait time before capture
2. Scroll page to trigger lazy loading
3. Wait for `networkidle` state
4. Check for fixed headers/footers affecting capture

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:

1. Ensure frontmatter is updated with `step-03-capture.md` in `stepsCompleted`
2. Load `./step-04-finalize.md` and follow its instructions

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:**
- Viewport resized to requested size
- Full-page screenshot captured
- Screenshot copied to project directory
- Screenshot verified accessible via `read_file`
- Frontmatter updated
- Menu presented with explicit HALT

❌ **FAILURE:**
- Screenshot not copied from temp directory
- Screenshot not verified as accessible
- Missing viewport resize before capture
- Proceeding to next step without user selecting Continue
