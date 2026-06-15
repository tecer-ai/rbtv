# Comment Implementation Protocol

The MANDATORY protocol ANY agent follows whenever it IMPLEMENTS hypresent review comments or makes comment-driven changes to an HTML artifact — regardless of entry path (a human gate, an agent-tagged instruction block, or a direct owner request). The comment thread is the HUMAN's record; the agent never closes it.

## Locate the Comments First

Comments live in TWO fixed places in EVERY hypresent-saved file — identical whether the file is a deck or a self-contained page. Read both before acting. NEVER grep to discover the format.

| Source | Where in the file | Holds |
|--------|-------------------|-------|
| Agent-instruction block | First child of `<head>` — an HTML comment delimited `===== HYPRESENT AGENT INSTRUCTIONS =====` … `===== END HYPRESENT AGENT INSTRUCTIONS =====` | ONLY agent-tagged, unresolved threads. Each entry carries `[agent:N]`, `target: [data-hyp-agent~="N"]`, `context`, `instruction`, any `reply:` lines, `author`, `date`. |
| Comment island | Near the end of `<body>` — `<script type="application/json" id="hyp-comments">…</script>` | EVERY thread — including untagged and resolved — with full `anchor`, `body`, `replies`, and `resolved` state. |

1. Read the file's first ~60 lines: the agent block lists every agent-tagged change with its copy-pasteable `[data-hyp-agent~="N"]` target selector.
2. Parse the `#hyp-comments` island for the complete thread set. Untagged comments appear ONLY there, never in the block — reading the block alone misses them.

## Four Invariants

| # | Invariant | Rule |
|---|-----------|------|
| 1 | Version, never overwrite | NEVER edit the file you were handed. Copy it first, edit the copy. |
| 2 | Reply, never resolve | Record what you did as a reply under your own agent identity. NEVER resolve or delete a comment thread — only the human owner resolves. |
| 3 | Untag, never orphan | After applying an agent-tagged instruction, remove ONLY the `data-hyp-agent` tag (so the auto-generated agent block drops the entry). The comment thread itself stays, unresolved and visible. |
| 4 | Re-wire on move/delete | A kept comment MUST always point at a surviving element. When its target moves or is deleted, re-anchor it per the Delete Handling table — NEVER let a comment go orphaned or silently vanish. |

## Versioned Copy

The file handed to the agent is **v1**. Each edit pass writes a NEW file; the original stays byte-untouched.

| Situation | New filename |
|-----------|--------------|
| `pitch.html` handed in (no version suffix present) | First edit pass → `pitch-v2.html` |
| `pitch-v3.html` is the highest existing version | Next edit pass → `pitch-v4.html` |

Rule: scan the folder, take the highest `-vN` suffix (treating an unsuffixed original as v1), write `-v{N+1}`. Apply ALL of this pass's comment changes inside that one new file. Save via the hypresent Save-As path (`/api/deck-save` or `handle_save_as`) — the comment island (`#hyp-comments`) travels with the copy.

## Per-Comment Procedure

For EACH comment the agent implements, in the new versioned copy:

1. Apply the requested change to the artifact.
2. Add a reply to that comment thread with author EXACTLY the agent's own identity in the form `{agent-name} ({role} agent)` — e.g. the designer agent Vivian signs `Vivian (designer agent)` — stating concisely what was changed and where.
3. If the comment was agent-tagged: remove the `data-hyp-agent` token for that id from the (new) target element. This drops the entry from the regenerated `HYPRESENT AGENT INSTRUCTIONS` block on save — it does NOT touch the thread.
4. Leave the thread UNRESOLVED. The human owner reviews the agent's reply and resolves (or reopens) it.

## Delete Handling

When a comment asks to delete a slide or an element, the comment cannot stay anchored to something that no longer exists. Re-wire it to the nearest surviving owner so the human still sees the request and the agent's reply:

| Comment requested | After the agent applies it | Re-anchor the comment to |
|-------------------|-------------------------|--------------------------|
| Delete an ELEMENT inside a slide | The element is gone; the slide remains | The slide (`<section>`) that contained the deleted element |
| Delete a whole SLIDE | The slide is gone | The immediately PREVIOUS slide (`<section>`); if the deleted slide was first, the new first slide |

In both cases the agent still adds its `{agent-name} ({role} agent)` reply (e.g. "Deleted the second bullet as requested — comment re-anchored to this slide") and leaves the thread unresolved for the owner.

## Re-Anchoring Mechanics

The runtime resolves a kept comment to its element on every move via `reanchorAfterMove()` (`studio/hypresent/runtime/js/comments.js`). After restructuring the copy:

- Operating through the app/bridge: moves and the Delete-Handling re-anchors flow through the comment API (`reply`, `setAgentInstruction(id,false)`, anchor updates) — let the runtime re-anchor, then verify every kept thread is anchored (none showing `unanchored`).
- Editing raw HTML directly: preserve the `#hyp-comments` island verbatim except for the entries you touch; for each touched entry update its `anchor` to the surviving element and append the reply object `{author:"{agent-name} ({role} agent)", body, createdAt}`. NEVER drop a thread, its `replies`, or its `resolved:false` state.

## Failure Modes

| Defect | Why it violates the protocol |
|--------|------------------------------|
| Editing the original file in place | Breaks Invariant 1 — the owner loses the pre-change version. |
| Resolving or deleting a thread after applying it | Breaks Invariant 2 — the owner's resolve decision is theirs, not the agent's. |
| Removing a thread instead of just its `data-hyp-agent` tag | Breaks Invariant 3 — destroys the human-facing record. |
| A kept comment left orphaned after a slide/element delete | Breaks Invariant 4 — the request and the agent's reply silently disappear. |
| Replying under an author that is not the agent's own `{agent-name} ({role} agent)` identity | The owner can no longer tell agent actions from human notes. |
