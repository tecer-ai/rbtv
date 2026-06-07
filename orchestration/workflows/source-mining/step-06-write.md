---
name: step-06-write
description: Apply resolutions, write final outputs, cleanup runtime folder
nextStepFile: null
workflowFile: ./workflow.md
---

# Step 6: Write

**Progress: Step 6 of 6** — Final step

---

## STEP GOAL

Write final outputs to vault locations and clean up the runtime folder.

---

## MANDATORY EXECUTION RULES

- 🛑 RECONCILE MODE: target docs are OVERWRITTEN. Trust git for v1 record.
- 🛑 STUDY MODE: study doc is a NEW file at user-confirmed destination.
- 🧹 ALWAYS auto-delete `<runtime_root>` after final write succeeds.
- 🔧 Invoke `sb-vault-ops` skill before vault writes; invoke `sb-vault-integrity` after creating new files.

---

## MANDATORY SEQUENCE

### 1. Read State

Read:
- `<runtime_root>/manifest.json`
- Reconcile: `<runtime_root>/synthesis/delta-draft.md`, `open-questions.md` (with answers)
- Study: `<runtime_root>/synthesis/study-draft.md`, `reflection-prompts.md` (with answers)

### 2A. Reconcile Mode Write

#### 2A.1 Fold resolutions into delta

For each answered open question, append a `### Change` block to delta-draft.md capturing the user's resolution as Source.

#### 2A.2 Apply changes to target docs

Invoke `sb-vault-ops` skill before writing. For each target in `inputs.targets`:
- Apply every `### Change` block where Source matches that target
- Overwrite the target file in place

#### 2A.3 Write delta file — CONDITIONAL

Count `applied_changes` = `### Change` blocks applied to target docs in 2A.2 (exclude "considered / no change" items). Count `targets_modified`.

| Condition | Action |
|-----------|--------|
| `applied_changes` >= 3 OR `targets_modified` > 1 | WRITE the delta file (procedure below) — it earns its place as a multi-change summary. |
| Otherwise (<= 2 changes confined to a single target, including the 0-change case) | SKIP the delta file. Git diff + commit message are the record. Fold the change summary AND any "considered / no change" notes into the Step 3 final report instead. NEVER create a delta file for a trivial change set. |

WRITE procedure:
- Resolve delta path. Default: `<target_dir>/<target_basename>-delta.md`. Override via `rbtv-output-resolution` rule if CLAUDE.md routing applies.
- Write the final delta-draft.md to that path. Invoke `sb-vault-integrity` after creation.

### 2B. Study Mode Write

#### 2B.1 Apply user shaping to study draft

For each answered reflection prompt, integrate the user's response into study-draft.md (reorder sections, expand chosen tensions, drop deprioritized themes).

#### 2B.2 Write study doc

Resolve destination from `inputs.study_destination`. Invoke `sb-vault-ops` skill. Write the final study-draft.md to that path.

Invoke `sb-vault-integrity` after creation.

### 3. Final Report

Present:

| Item | Detail |
|------|--------|
| Mode | reconcile / study |
| Run ID | <run_id> |
| Targets overwritten (reconcile) | <list> |
| Delta files (reconcile) | <list, or "none — N change(s) reported inline per 2A.3"> |
| Study doc (study) | <path> |
| Total source line span processed | <total> |
| Sub-agent calls | <count> (Haiku: <N>, Opus: <M>) |
| Run duration | <wall-clock> |

### 4. Cleanup Runtime

Delete `<runtime_root>/` recursively. Confirm to user:

```
Runtime folder <runtime_root> deleted.
```

If parent `.rbtv-runtime/source-mining/` is now empty, delete it. If `.rbtv-runtime/` itself is empty, leave it (user may have other tools using it).

### 5. Step Menu

**YOLO bypass:** if `manifest["yolo"] == true`, skip this menu and exit cleanly with a one-line "Workflow complete" report. Otherwise:

| Option | Action |
|--------|--------|
| **[D] Done** | Workflow complete |

HALT and WAIT.

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:** Final outputs written to vault; runtime folder cleaned up.

❌ **FAILURE:** Vault writes fail mid-way (partial state); cleanup skipped; manifest not updated.
