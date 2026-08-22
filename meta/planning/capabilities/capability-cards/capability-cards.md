---
description: Render one uniform card per exposed mirror resource from exposure.csv declarations.
---
# capability-cards

Render one uniform card per exposed resource across the mirror's components. Cards are built live from each component's `exposure.csv`, so the catalog cannot drift.

## Procedure

```bash
python 3-resources/tools/rbtv/meta/planning/capabilities/capability-cards/tool/capability_cards.py list
python 3-resources/tools/rbtv/meta/planning/capabilities/capability-cards/tool/capability_cards.py list --json
python 3-resources/tools/rbtv/meta/planning/capabilities/capability-cards/tool/capability_cards.py show <part-id>
```

## I/O

- Input: `--root` path (default `.rbtv/mirror/` relative to cwd) and, for `show`, a `part-id`.
- Output: cards on stdout; JSON array with `--json`. Stderr carries warnings for missing manifests, malformed headers, and short rows.
- Exit codes: `0` success, `1` unknown part-id, `2` missing root path.

## Example

```bash
python tool/capability_cards.py show console-master-prompt
```

```text
part-id: console-master-prompt
part-kind: prompt
component: master-agent
module: meta
method: agents.md
entry-point: prompts.csv#console-master-prompt
rbtv-cli: exhibit
description: —
```
