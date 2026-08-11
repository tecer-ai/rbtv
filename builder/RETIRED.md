# RETIRED — 2026-08-11, by owner ruling

**Do not follow anything in this folder.** It is kept for history only.

## What is retired

The previous-generation "create any component" system:

- `skills/create-component/` (`rbtv-create-component`)
- `workflows/component-creation/` (steps, templates, data)
- `workflows/component-review/` (steps, data, `scripts/measure-component.py`)

**Superseded by** the meta/planning reference set (`.rbtv/mirror/meta/planning/references/` — the
`file-prompt.md` / `file-task.md` / `exposure.md` kind guides and the component-shape canon) and the
forge workflow. Component structure, naming, and the exposure/seat canon are defined there now; this
folder's `component-patterns.md`, `rbtv-architecture.md`, and `rule-design-guide.md` predate that
canon and disagree with it.

## What is NOT retired

`rules/source-of-truth.md` — the `rbtv-source-of-truth` rule ("never edit installed `.claude/`
copies") is LIVE and still installs from this module. It is generic infrastructure, not
component-creation guidance, and workspace `CLAUDE.md` files cite it by name. It was deliberately
left in `admin/install/module-manifest.json` when the `create-component` skill entry was removed.

## Effect of the retirement

- `admin/install/module-manifest.json` no longer installs `rbtv-create-component`. A workspace that
  already has `.claude/skills/rbtv-create-component/` loses it on the next `python install.py`
  (re-install removes the previous install's file list).
- No files were deleted. Every path above still resolves, so historical references do not break.
- `exposure.csv` still carries the `measure-component` row pointing at
  `workflows/component-review/scripts/measure-component.py`. The script still runs; it is an orphan
  of a retired workflow and is left in place rather than silently dropped from the tool inventory.
