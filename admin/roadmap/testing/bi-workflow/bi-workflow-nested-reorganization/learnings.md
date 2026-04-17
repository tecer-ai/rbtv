# Learnings - BI Workflow Nested Reorganization

> **Purpose:** Capture system improvement opportunities discovered during plan execution.
> **Format:** Append entries as discoveries occur. Process during pN-compound task.

---

## Entries

<!-- Learning entries will be appended below this line -->

### 2026-03-17 — Execution of bi-workflow-nested-reorganization plan

**System improvement: ripgrep on Windows (Cursor environment)**
- `rg` is not in the system PATH on this Windows machine
- Cursor bundles ripgrep at: `C:\Program Files\cursor\resources\app\node_modules\@vscode\ripgrep\bin\rg.exe`
- Use `$rg = "C:\Program Files\cursor\resources\app\node_modules\@vscode\ripgrep\bin\rg.exe"; & $rg ...` pattern in PowerShell
- Memory entry written to `.claude/memory/tools/` (see below)

**System improvement: PowerShell vs bash syntax**
- `&&` is not valid in PowerShell — use `;` to chain commands
- This caused the first grep attempt to fail; retry with `;` succeeded

**Validation finding: `step-02-milestone-select.md` `../bi-mN/` references**
- After Phase 2, `../bi-m1/` through `../bi-m4/` in `step-02-milestone-select.md` are the CORRECT updated paths
- These look like stale patterns in grep output but are valid — from `steps-c/`, `../` goes to `bi-business-innovation/`, then into child `bi-m1/`
- Future validators: treat these matches as expected, not stale

**No process improvements identified** — the 9-phase plan with checkpoint gates worked well for a ~200-file reorganization. Pattern A-F taxonomy was effective for systematic path fixes.
