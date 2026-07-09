---
name: rbtv-safe-move
description: "Move or rename a file or folder in ONE operation that also finds and fixes every reference to it — markdown links, wikilinks, frontmatter paths, config paths, and code imports (matched structurally via ast-grep, never regex). Use WHENEVER you or the user need to relocate or rename a file or directory and keep its references intact, instead of moving by hand and grepping for callers. Two stateless calls: consult (dry-run — find, classify, and risk-grade every reference; changes nothing) then act (perform the git-aware move and auto-apply the safe fixes, surfacing the risky ones for you). Each prints a compact summary and files its full result as a report under .rbtv/runtime/safe-move/; a show subcommand slices records back out. Drift-safe via a hash handshake. Folder moves are the primary case."
---

# Safe Move

Move or rename a file/folder and fix every reference to it in one git-aware operation.

The tool is a deterministic Python package run in place from the RBTV source — it is NOT installed into `.claude/`.

- **Tool directory (this workspace):** `{rbtv_path}/core/tools/safe-move/`
- **Invoke:** `python -m safe_move <consult|act> ...` (run with the tool directory as the working directory)

**Before invoking, read `{rbtv_path}/core/skills/safe-move/safe-move-guide.md` IN FULL and follow it.** It carries the two-call workflow, the reference-class risk model, every option, the drift-safety contract, and what the tool does and does not do.
