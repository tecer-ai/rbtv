---
stepNumber: 2
stepName: 'convert'
nextStepFile: ./step-03-validate.md
---

# Step 02: Convert Diagrams

**Progress: Step 2 of 4** — Next: Validate Clarity

---

## STEP GOAL

Convert each Mermaid diagram to PNG using mmdc CLI with consistent settings.

---

## MANDATORY EXECUTION RULES

### Universal Rules

- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement

You are a Diagram Conversion Specialist. Execute conversions methodically, report progress clearly.

### Step-Specific Rules

- Process diagrams in file order (diagram 1 = first in file)
- Use consistent naming: `diagram_01.png`, `diagram_02.png`, etc.
- Apply consistent background (white) and width (1600px)
- Report each conversion result immediately
- Clean up temporary .mmd files after successful conversion

---

## MANDATORY SEQUENCE

### 1. Report Conversion Plan

Display conversion plan:

```
Converting {N} diagram(s) to PNG:

Output folder: {output_folder}
Settings: white background, 1600px width

Starting conversion...
```

### 2. Convert Each Diagram

For each Mermaid block in file order:

#### 2a. Extract Content

Extract Mermaid content (excluding code fences) and write to temporary file:
- Temp file: `{output_folder}/diagram_{NN}.mmd`
- NN = zero-padded number (01, 02, 03...)

#### 2b. Execute Conversion

Run mmdc command:

```bash
mmdc -i "{output_folder}/diagram_{NN}.mmd" -o "{output_folder}/diagram_{NN}.png" -b white -w 1600
```

#### 2c. Report Result

**On success:**
```
✓ Diagram {NN}: Converted successfully
```

**On failure:**
```
✗ Diagram {NN}: Conversion failed
  Error: {error message}
```

Store failed diagrams for final report.

#### 2d. Cleanup

Remove temporary `.mmd` file after successful conversion.

### 3. Report Conversion Summary

After all diagrams processed:

```
Conversion Complete:
- Successful: {count}
- Failed: {count}

Generated files:
{list of PNG files with paths}
```

If any failures, list them with error details.

### 4. Identify Diagrams for Validation

From step-01 state, list diagrams with 5+ nodes:

```
Diagrams requiring visual validation (5+ nodes):
- diagram_{NN}.png ({node_count} nodes)
...
```

If none require validation: "All diagrams have < 5 nodes. Skipping visual validation."

### 5. Present Menu Options

**Select an Option:**

- **[C] Continue** — Proceed to validate clarity (step-03)
- **[S] Skip Validation** — Skip to update Markdown (step-04)
- **[R] Retry Failed** — Retry failed conversions
- **[X] Exit Workflow** — Save current state, exit

ALWAYS halt and wait for user selection.

---

## MMDC COMMAND REFERENCE

| Option | Purpose | Default |
|--------|---------|---------|
| `-i` | Input .mmd file | Required |
| `-o` | Output file (.png, .svg, .pdf) | Required |
| `-b` | Background color | transparent |
| `-w` | Width in pixels | 800 |
| `-H` | Height in pixels | auto |
| `-t` | Theme (default, forest, dark, neutral) | default |

---

## ERROR HANDLING

| Error | Cause | Resolution |
|-------|-------|------------|
| Syntax error | Invalid Mermaid syntax | Report line number, suggest fix |
| Font not found | System font missing | Use default theme |
| Timeout | Complex diagram | Increase timeout or simplify |

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:

1. Ensure all successful PNGs are recorded
2. Load `./step-03-validate.md` and follow its instructions

ONLY when **[S] Skip Validation** is selected:

1. Skip step-03
2. Load `./step-04-update.md` and follow its instructions

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:**
- All diagrams attempted conversion
- Results reported for each diagram
- Temporary files cleaned up
- Failed diagrams documented with errors
- Menu presented with explicit HALT

❌ **FAILURE:**
- Skipping diagrams without attempting conversion
- Not reporting individual conversion results
- Leaving temporary .mmd files without cleanup
- Proceeding to next step without user selecting Continue
