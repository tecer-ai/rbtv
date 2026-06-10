---
name: 'step-02-measure'
description: 'Produce the deterministic measured baseline for the target component.'
nextStepFile: './step-03-investigate.md'
workflowFile: './workflow.md'
---

# Step 2: Measure

**Progress: Step 2 of 4** — Next: Investigate

---

## STEP GOAL

Establish the measured baseline — every figure computed, none estimated — and append it to the diagnosis document.

---

## MANDATORY EXECUTION RULES

- 🔢 EVERY figure comes from the script or an explicit `wc`/`grep` call visible in the transcript — a reasoned number is a defect (Diagnostic Method Requirement 1, `./data/efficiency-patterns.md`)
- 🛑 NEVER drop files from the measurement silently — the measured file count MUST match Step 1's tree

---

## MANDATORY SEQUENCE

### 1. Run the Measurement Script

```bash
python {rbtv_path}/builder/workflows/component-review/scripts/measure-component.py {target source root(s)}
```

The script emits two markdown tables: per-file metrics (lines, words, imperatives, conditional lines, cross-file refs) and duplicated blocks (shared 12-word shingle runs between file pairs). Non-zero exit = fix the invocation or path; never proceed on a failed run.

**Python unavailable?** Fall back per file: `wc -l`, `wc -w`; imperatives `grep -o -E '\b(MUST|NEVER|ALWAYS|STOP)\b' {file} | wc -l`; conditional lines `grep -c -i -E '(^| )(if|when) ' {file}`. Mark the duplication table `NOT MEASURED (no python)` — never substitute an impression for it.

### 2. Reconcile File Count

Compare the script's TOTAL row file count against Step 1's enumerated tree. A mismatch means files were missed (binary assets are expected gaps; markdown/code gaps are not) — resolve the discrepancy before continuing and record the resolution.

### 3. Append the Baseline

Append both tables to the diagnosis document under `## Measured Baseline`, plus a 3-line reading: the heaviest files by words, the top duplication pair, and the densest file by imperatives-per-words. No interpretation beyond those three lines — interpretation is Step 3's job, with evidence.

### 4. Present Menu

| Option | Action |
|--------|--------|
| **[C] Continue** | Proceed to Step 3 — Investigate |
| **[X] Exit** | Stop the review |

HALT and WAIT for user input.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:
1. Update the diagnosis document frontmatter: add `step-02-measure` to `stepsCompleted`
2. Load `./step-03-investigate.md` and follow its instructions

---

✅ **SUCCESS:** baseline tables in the document, file counts reconciled, every figure traceable to a command.
❌ **FAILURE:** estimated figures; silently missing files; interpretive conclusions written into the baseline.
