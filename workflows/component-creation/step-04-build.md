---
name: Build
description: Create all component files and update references.
nextStepFile: null
---

# Step 4: Build

**Goal:** Create all approved component files, verify compliance, and confirm what was built.

---

## Mandatory Sequence

### 1. Create Component Files

Write all files per the approved scaffold from Step 03. Write files in dependency order — backing files before thin loaders.

Never deviate from the approved scaffold without user confirmation.

### 2. Skills: Create Both Files

For any skill, create both:

1. **Backing file** (workflow, task, or agent) — all logic lives here
2. **Thin loader** (`SKILL.md`) — load instruction only, zero logic

The thin loader is invalid without its backing file. Never create a skill loader that points to a nonexistent file.

### 3. Compliance Verification

Verify each created file against `{rbtv_path}/workflows/component-creation/data/component-patterns.md`:

| Check | Applies to |
|-------|-----------|
| File within size limits | All files |
| Required frontmatter fields present | Workflow, step, command files |
| Forbidden frontmatter fields absent | Workflow, step files |
| Terminal step has `nextStepFile: null` | Last step file |
| Thin loader contains zero logic | Skills, commands |
| Paths use `{rbtv_path}` placeholder | All files |
| Every step ends with Step Menu + HALT | Step files |

If any check fails: fix the violation before presenting the summary.

### 4. Post-Build Instructions

**RBTV component:**

Re-run the installer to generate thin loaders in `.claude/`:

```bash
python install.py
```

**Non-RBTV component:** No install step needed.

### 5. Build Summary

Present:

| Item | Detail |
|------|--------|
| Files created | [list with full paths] |
| Files modified | [list, or "none"] |
| How to invoke | [exact invocation — skill name, command, or direct file path] |
| Install required? | [Yes — run `python install.py` / No] |

---

## Step Menu

| Option | Action |
|--------|--------|
| [D] Done | Workflow complete |

HALT and WAIT for user input.
