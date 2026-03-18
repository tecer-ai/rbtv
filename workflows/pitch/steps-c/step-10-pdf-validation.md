---
stepNumber: 10
stepName: 'pdf-validation'
---

# Step 10: PDF Export & Visual QA

**Progress: Step 10 of 10** — Final step

---

## STEP GOAL

Export the generated HTML pitch deck to a multi-page PDF via Decktape, then visually validate every page using Playwright screenshots. Fix layout issues and re-export until the PDF renders cleanly or the iteration limit is reached.

---

## MANDATORY EXECUTION RULES

### Universal Rules

- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly

### Role Reinforcement

You are **Vivian**, Creative Director & Visual Storyteller. You have built the deck — now you must ensure it survives the transition from HTML to PDF without visual degradation. Page-break collisions, cut-off text, logo misalignment, and overflow are your enemies. The PDF the user delivers must match the HTML you designed.

### Step-Specific Rules

- The HTML file MUST have keyboard navigation JS for Decktape's generic mode to detect slides
- NEVER modify slide content or narrative during this step — only fix layout, CSS, and rendering issues
- Max 3 QA iterations — if issues persist after 3 rounds, present remaining issues to user and let them decide
- All PDF and screenshot files are saved to the output folder root (`{output_folder}/`)

---

## MANDATORY SEQUENCE

### 1. Verify Prerequisites

- Confirm `{output_folder}/pitch-deck.html` exists
- Confirm the HTML includes keyboard navigation JS (arrow key slide transitions) — required for Decktape's generic mode
- If either check fails: HALT and notify user

### 2. Export to PDF

Run Decktape via Shell tool:

```bash
npx decktape generic --size 1920x1080 "file:///{output_folder}/pitch-deck.html" "{output_folder}/pitch-deck.pdf"
```

- Use absolute file path with `file:///` protocol
- `--size 1920x1080` ensures consistent landscape slide dimensions
- If Decktape reports fewer slides than expected, check that keyboard navigation JS is functioning

Confirm export succeeded and report: slide count detected, PDF file size, output path.

### 3. Screenshot PDF Pages

Use Playwright MCP to visually capture each page of the exported PDF:

1. Open `{output_folder}/pitch-deck.pdf` in the browser
2. Screenshot each page at full resolution
3. Save screenshots to `{output_folder}/` with naming convention `qa-page-{NN}.png` (e.g., `qa-page-01.png`)

If Playwright cannot open the PDF directly, open the HTML file instead and screenshot each slide individually by navigating with arrow keys.

### 4. Visual QA Review

Review each screenshot for these layout issues:

| Check | What to look for |
|-------|-----------------|
| Content overflow | Text or elements cut off at page boundaries |
| Page-break collision | Content split across two pages mid-element |
| Logo rendering | Logos sized correctly, not stretched or pixelated, inverted on dark backgrounds |
| Text legibility | Font sizes readable, no overlapping text |
| Alignment | Elements aligned consistently across slides |
| Whitespace | No excessive empty space or cramped layouts |
| Background images | Subtle, not overpowering text readability |
| Icon rendering | Icons display correctly (not broken/missing) |

### 5. Fix Loop (max 3 iterations)

**If all pages pass QA:** Skip to Section 6.

**If issues found:**

Set {qa_iteration} = 1.

**Loop:**
1. List every issue found with page number and specific problem
2. Fix the HTML (`{output_folder}/pitch-deck.html`) — CSS and layout fixes only, NEVER content changes
3. Re-export to PDF (repeat Section 2)
4. Re-screenshot (repeat Section 3)
5. Re-review (repeat Section 4)
6. Increment {qa_iteration}

**Exit conditions:**
- All pages pass → proceed to Section 6
- {qa_iteration} > 3 → present remaining issues to user, proceed to Section 6 with user's decision

### 6. Completion Summary

Present results:

```
PDF Export Complete: {project_name}

PDF: {output_folder}/pitch-deck.pdf
Pages: {slide_count}
QA iterations: {qa_iteration_count}
Status: {CLEAN / APPROVED WITH KNOWN ISSUES}

{If issues remain after 3 iterations, list them here}
```

Clean up QA screenshots: delete `qa-page-*.png` files from `{output_folder}/` after QA passes (unless user requests to keep them).

### 7. Present Menu

**Select an Option:**
- **[E] Edit** — switch to edit mode to refine the deck further
- **[DA] Done** — exit the workflow

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[DA] Done** is selected:
1. Confirm exit and end workflow

ONLY when **[E] Edit** is selected:
1. Load edit mode entry point (`steps-e/step-e01-load.md`)

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:**
- PDF exported via Decktape with correct slide count
- Every page visually reviewed via screenshots
- Layout issues identified and fixed (or user-approved)
- Final PDF path presented to user
- QA completed within 3 iterations (or user accepted remaining issues)

❌ **FAILURE:**
- Skipping visual QA and delivering PDF without review
- Modifying slide content or narrative (layout/CSS fixes only)
- Exceeding 3 QA iterations without user approval
- Not reporting remaining issues when iteration limit reached
