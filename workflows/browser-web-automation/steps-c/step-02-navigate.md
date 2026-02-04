---
stepNumber: 2
stepName: 'navigate'
nextStepFile: ./step-03-capture.md
---

# Step 02: Navigate

**Progress: Step 2 of 4** — Next: Capture

---

## STEP GOAL

Navigate to the target URL and ensure the page is fully loaded and ready for capture.

---

## MANDATORY EXECUTION RULES

### Universal Rules

- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement

You are a Browser Automation Specialist. Continue methodical approach.

### Step-Specific Rules

- Use Playwright MCP tools exclusively
- Wait for page to fully load before proceeding
- Handle navigation failures gracefully

---

## MANDATORY SEQUENCE

### 1. Execute Navigation

Use Playwright MCP to navigate:

```
mcp_cursor-ide-browser_browser_navigate
url: [target_url from session document]
```

### 2. Wait for Page Load

Wait for page to reach stable state:

```
mcp_cursor-ide-browser_browser_wait_for
state: "networkidle"
timeout: 10000
```

**Wait states:**
- `load` — Load event fired
- `domcontentloaded` — DOM ready
- `networkidle` — Network idle (recommended)

### 3. Handle Navigation Issues

If navigation fails:

| Issue | Action |
|-------|--------|
| Timeout | Increase timeout, retry once |
| Blocked | Inform user, suggest alternatives |
| 404/Error | Report to user, ask for correction |
| Cookie consent | Take snapshot, click consent button |

### 4. Take Accessibility Snapshot

Get page structure for potential interactions:

```
mcp_cursor-ide-browser_browser_snapshot
```

Report page title and key elements detected.

### 5. Report Navigation Status

```
Navigation successful.
- URL: {current_url}
- Title: {page_title}
- Status: Ready for capture
```

### 6. Update State

Add `step-02-navigate.md` to `stepsCompleted` in session document frontmatter.

Update target status from `pending` to `navigated`.

### 7. Present Menu Options

**Select an Option:**

- **[C] Continue** — Proceed to screenshot capture (step-03)
- **[I] Interact** — Click elements or enter text before capture
- **[R] Retry** — Navigate again with different settings
- **[X] Exit Workflow** — Save current state, exit

ALWAYS halt and wait for user selection.

---

## INTERACTION SUB-WORKFLOW

If **[I] Interact** is selected:

1. Display element refs from snapshot
2. Ask user which element to interact with
3. Execute interaction:
   - Click: `browser_click` with `elementRef`
   - Type: `browser_type` with text
4. Wait for page update
5. Take new snapshot
6. Return to menu

---

## TROUBLESHOOTING

### Website Blocks Automation

If navigation fails due to blocking:
1. Try alternative URLs if available
2. Ask user for manual screenshots
3. Inform user of limitations
4. Suggest using a different approach

### Page Not Fully Loaded

If content appears incomplete:
1. Increase wait timeout
2. Use `browser_wait_for` with specific selectors
3. Wait for `networkidle` state
4. Check for lazy-loaded content

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:

1. Ensure frontmatter is updated with `step-02-navigate.md` in `stepsCompleted`
2. Load `./step-03-capture.md` and follow its instructions

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:**
- Page navigated successfully
- Page load confirmed (networkidle or element present)
- Snapshot taken for reference
- Frontmatter updated
- Menu presented with explicit HALT

❌ **FAILURE:**
- Navigation without waiting for load
- Proceeding without confirming page state
- Proceeding to next step without user selecting Continue
