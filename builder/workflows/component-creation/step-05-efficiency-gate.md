---
name: 'step-05-efficiency-gate'
description: 'Check the files built this session against the Create-Time Gate before ship.'
nextStepFile: null
workflowFile: './workflow.md'
dataFile: '../component-review/data/efficiency-patterns.md'
---

# Step 5: Efficiency Gate

**Progress: Step 5 of 5** — Final step

---

## STEP GOAL

Catch token-waste patterns in the component while it is still on the bench — every newly built component passes the Create-Time Gate before ship.

---

## MANDATORY EXECUTION RULES

- 📋 Load the gate JIT: read ONLY the "Create-Time Gate" section of `{rbtv_path}/builder/workflows/component-review/data/efficiency-patterns.md` — the full taxonomy is the review workflow's load, not this gate's
- 🛑 A failed check is FIXED or explicitly ACCEPTED by the owner — never silently passed

---

## MANDATORY SEQUENCE

### 1. Collect the Session's Files

The gate's input is the "Files created" + "Files modified" lists from Step 4's Build Summary. Structural edits count; pure doc-sync edits (README, modules/, manifest) are exempt.

### 2. Measure

```bash
python {rbtv_path}/builder/workflows/component-review/scripts/measure-component.py {files from step 1}
```

Python unavailable → per file: `wc -l`, `wc -w`; mark the duplication table `NOT MEASURED (no python)`.

### 3. Evaluate the Eight Gate Checks

Evaluate each Create-Time Gate row against the new files, using the measured tables as evidence for checks 1 (duplicated blocks), 5, 6 (size limits per `./data/component-patterns.md`), and 8 (the cognitive-load proxy columns — conditional / arbitration / max prose run / open-delib). Check 8's proxies are directional: a high score the build can justify as earned (well-sequenced, irreducible judgment) is owner-accepted, not auto-failed.

### 4. Present the Gate Report

No violations → present the measured table + one line: "Efficiency gate: clean (8/8)."

Violations → present:

| # | Gate check | File | Evidence | Proposed fix |
|---|-----------|------|----------|--------------|

### 5. Fix-or-Accept Loop

| Option | Action |
|--------|--------|
| **[F] Fix** | Apply the proposed fixes, then re-run this gate from action 2 |
| **[A] Accept** | Owner accepts the named violations — record each acceptance in the Build Summary ("gate: accepted #N — {reason}") |
| **[D] Done** | Available ONLY when the gate is clean or every violation is accepted |

HALT and WAIT for user input.

---

## CRITICAL STEP COMPLETION NOTE

Terminal step — no next step file. On **[D] Done**, the build is complete; restate the Build Summary with the gate line appended (clean, or accepted violations listed).

---

✅ **SUCCESS:** every new file measured, 8 checks evaluated with evidence, violations fixed or owner-accepted on record.
❌ **FAILURE:** skipping the gate for "small" components; loading the full taxonomy instead of the gate section; passing a violation without an acceptance record.
