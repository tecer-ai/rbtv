---
stepNumber: 4
stepName: 'update'
nextStepFile: null
---

# Step 04: Update Markdown

**Progress: Step 4 of 4** — Final Step

---

## STEP GOAL

Replace Mermaid code blocks with image references and complete the conversion workflow.

---

## MANDATORY EXECUTION RULES

### Universal Rules

- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement

You are a Diagram Conversion Specialist. Ensure clean, portable Markdown output.

### Step-Specific Rules

- NEVER modify target Markdown without explicit user confirmation
- Preview changes before applying
- Use relative image paths only
- Preserve all non-Mermaid content exactly
- Maintain diagram order (diagram N in file = image N in folder)

---

## MANDATORY SEQUENCE

### 1. Preview Changes

Prepare updated Markdown content where each Mermaid block is replaced by:

```markdown
![Diagram NN]({file_name}_mmdc/diagram_{NN}.png)
```

Present preview to user:

```
Proposed Changes:

The following Mermaid blocks will be replaced with image references:

| Block # | Original Lines | Replacement |
|---------|---------------|-------------|
| 1 | Lines {start}-{end} | ![Diagram 01]({folder}/diagram_01.png) |
| 2 | Lines {start}-{end} | ![Diagram 02]({folder}/diagram_02.png) |
...

Example (first replacement):

Before:
```mermaid
flowchart TD
    A --> B
```

After:
![Diagram 01]({folder}/diagram_01.png)
```

### 2. Confirm Changes

**Critical:** HALT and wait for explicit confirmation.

```
Ready to update {filename}?

- {N} Mermaid blocks will be replaced with image references
- Original file will be modified
- Images are in: {output_folder}

Type 'yes' or select [A] Apply to proceed.
```

Do NOT proceed without user confirmation.

### 3. Apply Changes (After Confirmation Only)

1. Read current file content
2. Replace each Mermaid block with corresponding image reference
3. Write updated content to file
4. Verify file was written successfully

### 4. Generate Completion Report

```
Conversion Complete!

Summary:
- Target file: {filename}
- Diagrams converted: {count}
- Output folder: {output_folder}
- Failed conversions: {count or 'none'}

Generated images:
{list of PNG files}

The Markdown file now uses image references that render in any Markdown viewer.
```

### 5. Present Menu Options

**Select an Option:**

- **[D] Done** — Complete workflow
- **[V] View Result** — Open updated Markdown file
- **[U] Undo** — Restore original Mermaid blocks
- **[R] Reconvert** — Restart workflow for this file

ALWAYS halt and wait for user selection.

---

## IMAGE REFERENCE FORMAT

| Element | Format |
|---------|--------|
| Alt text | `Diagram NN` (NN = diagram number) |
| Path | Relative to Markdown file location |
| Folder | `{file_name}_mmdc/` |
| File | `diagram_{NN}.png` |

**Example:**
- Markdown: `docs/architecture.md`
- Image ref: `![Diagram 01](architecture_mmdc/diagram_01.png)`

---

## CONSTRAINTS

| Constraint | Description |
|------------|-------------|
| Confirm before write | Never modify target Markdown without explicit confirmation |
| No content drift | Preserve all non-Mermaid content exactly |
| Relative links only | Image links must be relative to Markdown file location |
| Deterministic naming | Re-running should not rename existing outputs |
| Diagram order preserved | Diagram N in file maps to image N in output folder |

---

## OUTPUT STRUCTURE

```
{target_dir}/
├── {target_file}.md          # Updated with image references
└── {file_name}_mmdc/
    ├── diagram_01.png
    ├── diagram_02.png
    └── ...
```

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[D] Done** is selected:

1. Confirm all changes were applied successfully
2. Report final statistics
3. End workflow

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:**
- Preview shown before any modifications
- Explicit user confirmation obtained
- All Mermaid blocks replaced correctly
- Relative image paths used
- Non-Mermaid content preserved exactly
- Completion report generated
- Menu presented with explicit HALT

❌ **FAILURE:**
- Modifying file without user confirmation
- Using absolute image paths
- Corrupting non-Mermaid content
- Missing diagrams in replacement
- Not providing undo option
