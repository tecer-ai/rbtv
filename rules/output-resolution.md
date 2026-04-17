---
name: rbtv-output-resolution
description: "Smart-component behavior standard — RBTV components must read workspace CLAUDE.md routing, propose an output path with reasoning, and confirm with the user before writing. Never blind-prompt for a path."
---

# Output Resolution

When an RBTV component (skill, command, workflow) produces an output file, resolve the destination by this procedure.

## Resolution steps

1. Read the workspace root CLAUDE.md. Look for a `## File Routing` heading. Inside, read the routing table — specifically the content between the `<!-- file-routing-start -->` and `<!-- file-routing-end -->` HTML comment markers.
2. Match the component's output type (e.g. `pitch`, `planning`, `meeting-summary`, `writing`, `doc`, `create-component`, `product-discovery`, `business-innovation`, `design-extraction`, `tone-extraction`) to an entry in the routing table.
3. If the matched route points to a subdirectory that has its own CLAUDE.md with a `## File Routing` block, read it for further refinement. Stop at a leaf path or at a path containing an unresolved variable (e.g. `{client}`, `{project}`, `{prospect}`).
4. Infer runtime variables from conversation context. Variables like `{client}` or `{project}` are resolved from what the user has already said in the current session. Do NOT ask about them blindly — only ask if the conversation truly does not specify.
5. Propose the full resolved path to the user with reasoning. Example: "I'll write this pitch to `tecer-biz/clients/SPSP/pitch-2026-04.md` because the routing says `pitch` → `clients/{client}/` and you mentioned SPSP."
6. Wait for confirmation or redirect. The user may approve, edit the path, or redirect entirely. Do not write until confirmed.

## Degraded modes

- If no `## File Routing` block exists anywhere in the workspace hierarchy, inform the user that `/rbtv-output-routing` has not been run, then ask ONCE for this write's output path. Do not block the workflow.
- If routing is ambiguous (multiple candidate routes, or a variable the conversation does not resolve), ask a SPECIFIC question ("The routing sends pitches to either `clients/` or `prospects/`. Is this for a current client or a prospect?"). Never fall back to a generic "where should this go?" prompt.
- If the user redirects to a path outside the routing table, write where the user said, then note the divergence and suggest running `/rbtv-output-routing` so the routing catches this case next time.

## File routing block format

A `## File Routing` section in a CLAUDE.md contains a markdown table with columns "Output type" and "Route". The table MUST be wrapped between `<!-- file-routing-start -->` and `<!-- file-routing-end -->` HTML comment markers so `/rbtv-output-routing` can edit the block idempotently without touching surrounding CLAUDE.md content. Output-type names must match the list in Resolution step 2 above.

## Scope

This rule governs output path resolution ONLY. It does not govern:
- What content to write (each component's own workflow owns that).
- Whether to write at all (component decides based on task completion).
- File-naming conventions within the resolved directory (component decides, or a more specific rule governs).
