---
name: rbtv-output-resolution
description: "Smart-component behavior standard — RBTV components must use conversation context and vault conventions to propose an output path, then confirm with the user before writing."
---

# Output Resolution

When an RBTV component (skill, command, workflow) produces an output file, resolve the destination by this procedure.

## Resolution steps

1. Use conversation context to determine the destination. The user's current topic, project, and area usually make the path obvious.
2. Read the relevant CLAUDE.md files (workspace root, project-specific) to understand folder structure and placement rules.
3. Propose the full resolved path to the user with reasoning. Example: "I'll write this pitch to `tecer-biz/prospects/spsp/presentations/pitch-2026-04.md` because you mentioned SPSP and their presentations go in the prospect folder."
4. Wait for confirmation or redirect. The user may approve, edit the path, or redirect entirely. Do not write until confirmed.

## When the path is ambiguous

Ask a SPECIFIC question based on what you know. Example: "Is this for a current client or a prospect?" Never fall back to a generic "where should this go?" prompt.

## Scope

This rule governs output path resolution ONLY. It does not govern:
- What content to write (each component's own workflow owns that).
- Whether to write at all (component decides based on task completion).
- File-naming conventions within the resolved directory (component decides, or a more specific rule governs).
