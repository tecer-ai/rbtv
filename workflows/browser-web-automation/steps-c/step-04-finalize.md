---
stepNumber: 4
stepName: 'finalize'
---

# Step 04: Finalize

**Progress: Step 4 of 4** — Final Step

---

## STEP GOAL

Verify all captured assets, present summary, and complete the workflow.

---

## MANDATORY EXECUTION RULES

### Universal Rules

- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement

You are a Browser Automation Specialist. Complete your work with verification.

### Step-Specific Rules

- Verify all screenshots are accessible
- Present complete summary of captured assets
- Handle research mode with multiple targets

---

## MANDATORY SEQUENCE

### 1. Verify All Screenshots

For each screenshot captured:
1. Verify file exists at project path
2. Confirm file is readable via `read_file`
3. Note any missing or inaccessible files

Report verification status:
```
Screenshot verification:
- ✅ {filename1}: Accessible
- ✅ {filename2}: Accessible
- ❌ {filename3}: Not found (if applicable)
```

### 2. Handle Research Mode (Multi-Target)

If operation mode is Research with multiple targets:

Check session document for remaining targets:
- If targets pending: "There are {N} more targets. Process next?"
- If all complete: Proceed to summary

### 3. Present Completion Summary

```
Browser automation complete.

Session: {session-name}
Mode: {capture|research|local|interactive}
Targets processed: {count}

Files created:
{list each file with full path}

Screenshots captured:
- {count} desktop ({count} × 1440×900)
- {count} tablet ({count} × 768×1024) (if applicable)
- {count} mobile ({count} × 375×812) (if applicable)

Output folder: {output_folder}/screenshots/
```

### 4. Update State

Add `step-04-finalize.md` to `stepsCompleted` in session document frontmatter.

Update all target statuses to `complete`.

### 5. Present Menu Options

**Select an Option:**

- **[D] Done** — Exit workflow successfully
- **[N] Next Target** — Process another URL (research mode)
- **[V] View Screenshots** — Load screenshots for visual review
- **[S] Start New** — Begin new browser session

ALWAYS halt and wait for user selection.

---

## MULTI-TARGET HANDLING

For research mode with multiple URLs:

1. After completing one target, check for more
2. If more targets exist, offer to continue
3. Track progress in session document
4. Final summary includes all targets

---

## POST-WORKFLOW ACTIONS

### Load for Analysis

If user wants to analyze captured screenshots:
- Suggest visual design extraction workflow
- Offer to load screenshots into context

### Additional Captures

If user needs more screenshots:
- Can start new session
- Can add targets to existing session (research mode)

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[D] Done** is selected:

1. Confirm all files saved successfully
2. Present final summary
3. Exit workflow gracefully

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:**
- All screenshots verified accessible
- Complete summary presented
- Session document updated with all steps
- User confirmed completion

❌ **FAILURE:**
- Screenshots not verified
- Incomplete summary
- Missing files not reported
- Proceeding without user confirmation
