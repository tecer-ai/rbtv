---
stepNumber: 2
stepName: 'setup'
nextStepFile: ./step-03-capture.md
---

# Step 02: Environment Setup

**Progress: Step 2 of 4** — Next: Screenshot Capture

---

## STEP GOAL

Start local HTTP server and prepare the environment for screenshot capture.

---

## MANDATORY EXECUTION RULES

### Universal Rules

- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement

You are a Design QA Specialist. Continue your methodical approach.

### Step-Specific Rules

- Start HTTP server in directory containing HTML files
- Use port 8000+ (check availability)
- Verify server is running before proceeding
- Confirm target file is accessible via browser

---

## MANDATORY SEQUENCE

### 1. Identify Directory

Determine the directory containing the target HTML file(s) from step-01 frontmatter.

Report:
- "Target directory: {path}"
- "Files to validate: {file-list}"

### 2. Check for Running Server

Check if a local server is already running:
- If Python server active on 8000+: "Server already running at http://localhost:{port}"
- If no server: proceed to start one

### 3. Start Local HTTP Server

Execute command to start server:

```bash
# Python (preferred)
python -m http.server 8000

# Alternative: Node.js
npx serve -p 8000
```

Start as background process if needed.

### 4. Verify Server Access

Confirm server is accessible:
- Navigate to `http://localhost:{port}/`
- Verify target HTML file(s) are accessible
- Report: "Server running. Target accessible at http://localhost:{port}/{filename}"

### 5. Prepare Screenshot Directory

Create screenshots directory:
- Path: `{target-directory}/{filename}_screenshots/`
- Report: "Screenshot output directory ready."

### 6. Update State

Add `step-02-setup.md` to `stepsCompleted` in output document frontmatter.

### 7. Present Menu Options

**Select an Option:**

- **[C] Continue** — Proceed to screenshot capture (step-03)
- **[R] Retry Setup** — Fix server issues and retry
- **[X] Exit Workflow** — Save current state, exit

ALWAYS halt and wait for user selection.

---

## PORT SELECTION

| Port | Use Case |
|------|----------|
| 8000 | Default Python http.server |
| 8080 | Alternative if 8000 busy |
| 3000 | Default for Node serve |
| 5000 | Alternative for Node |

Check `netstat` or `lsof` if port conflicts occur.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:

1. Ensure frontmatter is updated with `step-02-setup.md` in `stepsCompleted`
2. Load `./step-03-capture.md` and follow its instructions

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:**
- HTTP server running
- Target file(s) accessible via localhost
- Screenshot directory created
- Frontmatter updated
- Menu presented with explicit HALT

❌ **FAILURE:**
- Proceeding without server confirmation
- Server not accessible
- Proceeding to next step without user selecting Continue
