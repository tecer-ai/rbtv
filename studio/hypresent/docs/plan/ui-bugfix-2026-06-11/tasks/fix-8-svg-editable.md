---
execution_kind: code
executor: codex
allowed_workdir: C:\Users\henri\Documents\second-brain\3-resources\tools\rbtv\studio\hypresent
allowlist:
  - runtime/js/text-edit.js
  - runtime/js/selection.js
sandbox: workspace-write
commit_policy: none
test_command: NONE (conductor runs the e2e gate)
forbidden_ops:
  - git commit
  - git push
  - git reset
  - writes outside allowlist
  - external production API calls
  - --dangerously-bypass-approvals-and-sandbox
doubt_policy: halt
reviewer: claude-opus
---

## Sandbox + Approval
Run under `--sandbox workspace-write` + `-c approval_policy="never"`. Edit ONLY the two allowlisted files in the work-dir. Do not write anywhere else.

# Fix bug-8 — text boxes with an inline `<svg>` child cannot enter edit mode

## Goal
Make a text element that contains a decorative inline `<svg>` child editable on double-click, by adding `"svg"` to the inline-tag allow-set in BOTH gate functions. One bounded deliverable: two one-line set additions.

## Context Snapshot (everything you need — do NOT read other files to "understand")
The editor refuses to enter text-edit on an element whose children include a tag NOT in an inline allow-set. Two functions carry an identical allow-set and BOTH must be patched:

1. `runtime/js/text-edit.js` — `const INLINE_TAGS = new Set([... "big" ]);` (around lines 41-46). The last current entry is `"big"`.
2. `runtime/js/selection.js` — inside `isTextEditable`, `const inlineTags = new Set([... "big" ]);` (around lines 66-71). The last current entry is `"big"`.

Both sets currently OMIT `"svg"`. The GSMM deck's `div.lead` / `div.map-legend` rows carry an inline `<svg class="map-mark">` icon, so they fail the child test and never become editable.

SVG roots and SVG descendants stay non-editable via SEPARATE guards already present in both files (`if (tag === "svg") return false;` and `if (isInsideSvg(el)) return false;`). So adding `"svg"` to the inline set does NOT make the svg icon itself editable — it only stops the svg child from disqualifying its TEXT parent. Do NOT touch those guards.

## Allowed Paths
- `runtime/js/text-edit.js`
- `runtime/js/selection.js`

## Forbidden Paths
- Every other file. No new files. No commits.

## Implementation Requirements (exact)
1. In `runtime/js/text-edit.js`, add the string `"svg"` as a new element of the `INLINE_TAGS` Set (append it after `"big"`). Keep formatting consistent with the surrounding entries.
2. In `runtime/js/selection.js`, add the string `"svg"` as a new element of the `inlineTags` Set inside `isTextEditable` (append it after `"big"`). Keep formatting consistent.
3. Change NOTHING else — not the `EXCLUDED_TAGS`/`excluded` sets, not the `isInsideSvg`/`tag === "svg"` guards, not any other logic.

## Validation (run before returning)
- `git --no-pager diff -- runtime/js/text-edit.js runtime/js/selection.js` → MUST show exactly two added `"svg"` entries (one per file), inside the INLINE_TAGS / inlineTags sets, and NO other change.
Report the command, its output, and EXIT code in `validation`.

## Commit Rule
Do NOT commit. Leave the two files modified in the working tree; the conductor reviews the diff and commits.

## Return Format (the five-field schema, exactly)
- `status`: DONE | DONE_WITH_NOTES | BLOCKED | DOUBT_ESCALATED | NEEDS_CONTEXT
- `landed`: files modified + the exact lines changed
- `validation`: each command, EXIT, WALL_MS, SKIPPED_COUNT (+reasons)
- `concerns`: anything noticed
- `open_questions`: any doubt that halted you
