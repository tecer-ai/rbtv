---
name: step-01-init
description: Gather and validate inputs, create runtime folder, write manifest
nextStepFile: ./step-02-slice-and-boundary.md
workflowFile: ./workflow.md
---

# Step 1: Init

**Progress: Step 1 of 6** — Next: Slice and Boundary Review

---

## STEP GOAL

Gather all inputs, validate, create the per-run runtime folder, and confirm with user before any source mining begins.

---

## MANDATORY EXECUTION RULES

- 🛑 NEVER read any source file directly — sub-agents do all source reading
- 📖 ALWAYS validate file paths exist before proceeding
- 🔒 NEVER overwrite an existing run-id folder (append `-2`, `-3` on collision)
- 💾 ALWAYS write `manifest.json` before halting

---

## MANDATORY SEQUENCE

### 1. Pick Mode

Ask the user:

> Which mode?
> - **reconcile** — update an existing document to reflect source decisions + user fixups
> - **study** — produce study notes from a long source

Wait for selection.

### 2. Gather Inputs

#### Reconcile mode

| Input | Required? | Format | Notes |
|-------|-----------|--------|-------|
| Source file(s) | 0..N | Vault-relative or absolute paths | Large files the orchestrator must NOT read |
| Context reference(s) | 0..N | Paths or URLs | Smaller refs (gists, specs, articles) the orchestrator MAY read |
| Target document(s) | 1..N | Vault-relative paths | Doc(s) to be reconciled and overwritten |
| User line-comments | Optional but recommended | One per line, `Line N: text` or `Lines N and M: text` | Authoritative — never overridden by source findings |
| Topic taxonomy | Optional | Comma-separated list | Categories sub-agents tag findings by. If skipped, sub-agents emit free-form topics — warn quality may drop |
| Decision criteria | Optional | One sentence | Custom definition of "decision" if domain-specific |

#### Study mode

| Input | Required? | Format | Notes |
|-------|-----------|--------|-------|
| Source file(s) | 1..N | Paths | Long source(s) to study |
| Context reference(s) | 0..N | Paths or URLs | Related material |
| Study destination | Required | Vault-relative path | Where the new study doc will be written |
| Focus questions | Optional | Multi-line | What to look for during extraction |
| Theme taxonomy | Optional | Comma-separated | If skipped, sub-agents emit free-form themes |

### 3. Validate Source Files

For each source path provided:

| Check | Action on fail |
|-------|----------------|
| File exists | Ask user to fix path |
| File is readable (any encoding) | Ask user for encoding override |
| File line count > 100 | Warn — workflow is overkill for short files |

DO NOT read content. Use `wc -l`-style metadata only (e.g., `python -c "print(sum(1 for _ in open(P)))"`).

### 4. Generate Run ID

`run_id = "<YYYY-MM-DD-HHMM>-<slug>"` where:
- timestamp = current local time
- slug = primary source basename → kebab-case, lowercase, alphanum + hyphens, max 30 chars

### 5. Create Runtime Folder

```
runtime_root = <workspace-root>/.rbtv-runtime/digest/<run_id>/
```

Create directory. On collision, append `-2`, `-3`, etc. to `run_id`.

### 6. Ensure .gitignore Coverage

Read workspace `.gitignore`. If it does not contain `.rbtv-runtime/`, append:

```
# RBTV digest runtime (auto-deleted after each run)
.rbtv-runtime/
```

If no `.gitignore` exists, create one with the above content.

### 7. Write manifest.json

Write `<runtime_root>/manifest.json`:

```json
{
  "run_id": "<run_id>",
  "mode": "reconcile" | "study",
  "started_at": "<ISO timestamp>",
  "current_step": "step-01-init",
  "completed_steps": [],
  "inputs": {
    "sources": ["<path>", ...],
    "contexts": ["<path-or-url>", ...],
    "targets": ["<path>", ...],
    "study_destination": "<path-or-null>",
    "comments": "<verbatim user-provided text or null>",
    "taxonomy": ["<topic>", ...],
    "decision_criteria": "<text or null>",
    "focus_questions": "<text or null>"
  },
  "boundaries": null,
  "outputs": {}
}
```

### 8. Confirm with User

Present:

```
Run created: <runtime_root>
Mode: <mode>
Sources: <list with line counts>
Contexts: <list>
Targets (reconcile) | Study destination (study): <path(s)>
Comments: <count of comment lines, or "none">
Taxonomy: <list or "free-form">
```

### 9. Step Menu

| Option | Action |
|--------|--------|
| **[C] Continue** | Proceed to Step 02 — slice and boundary |
| **[E] Edit inputs** | Restart input gathering |
| **[X] Exit** | Abort run; offer to delete runtime folder |

HALT and WAIT for user selection.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:

1. Update `manifest.json`: set `current_step = "step-02-slice-and-boundary"` and append `step-01-init` to `completed_steps`.
2. Load `./step-02-slice-and-boundary.md` and follow its instructions.

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:** Runtime folder exists with valid manifest.json; user confirmed input set.

❌ **FAILURE:** Sources not validated; runtime folder not created; manifest missing required fields; user not confirmed.
