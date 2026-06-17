# Comment Authoring Protocol

The MANDATORY protocol ANY agent follows to CREATE a new hypresent comment from scratch — its own review note, question, or an instruction for a coding agent — by raw-editing the HTML file with no hypresent app running. Authoring a comment NEVER touches existing threads; acting on existing comments (reply, resolve, implement) is the separate Comment Implementation Protocol.

## Where a Comment Lives

A hypresent comment is ONE thread object inside the `#hyp-comments` JSON island — `<script type="application/json" id="hyp-comments">[ … ]</script>` near the end of `<body>`. That island is the COMPLETE, authoritative record of every thread. Creating a comment = appending one valid thread object to that array (plus, for an agent-instruction, one attribute on the target element).

NEVER hand-write the head `===== HYPRESENT AGENT INSTRUCTIONS =====` block — it is auto-generated from the island on the next hypresent save and removed when no agent-tagged threads remain.

## Thread Object Schema

| Field | Value |
|-------|-------|
| `id` | String. The next integer ABOVE the highest existing `id` in the island (`"1"` if the island is empty). |
| `anchor` | Object `{hook, path, nativeId, contentHash, siblingIndex}` — see Build the Anchor. COMPUTE it; never fabricate. |
| `contextText` | `normalizeText(targetElement.textContent).slice(0, 80)` — the first 80 chars of the element's collapsed text. |
| `author` | The agent's OWN identity in the form `{agent-name} ({role} agent)` — e.g. `Vivian (designer agent)`. |
| `createdAt` | Current time as ISO-8601, e.g. `2026-06-16T21:09:12.352Z`. |
| `body` | The comment text — your note, question, or instruction. |
| `resolved` | `false`. Only the human owner resolves. |
| `replies` | `[]`. |
| `agentInstruction` | `true` ONLY if a coding agent should act on this comment; `false` for a human-facing note or question. |

Omit `editedAt` on a new comment.

## Build the Anchor — COMPUTE, never fabricate

The anchor is how the runtime re-finds the element. A wrong `contentHash` makes the comment load `unanchored` — no marker renders and the owner never sees it. Every field is an exact function of the target element. Compute each deterministically — run the runtime's own helpers over the parsed DOM, or replicate them in a script. NEVER eyeball them.

| Field | Rule |
|-------|------|
| `hook` | The element's `data-hyp-hook` attribute, or `null` if absent. |
| `nativeId` | The `id` of the nearest ancestor-or-self whose `id` does NOT start with `hyp-`; `null` if none exists. |
| `path` | Segments from the base down to the element, joined by `/`. Base = the `nativeId` element, or the document root if `nativeId` is `null`. Each segment is `{tag}:{nth}` — `tag` lowercased, `nth` = 1-based position among same-TAG siblings. Empty string if the element IS the base. |
| `contentHash` | `fnv1a32( normalizeText(textContent).slice(0, 32) )` — see Reference functions. |
| `siblingIndex` | 0-based index of the element among its siblings of the SAME tag AND same primary class signature (class tokens, excluding any `hyp-…` token). `0` if it has no parent. |

### Reference functions (replicate exactly)

```js
normalizeText(s) { return (s || "").replace(/\s+/g, " ").trim(); }

fnv1a32(input) {
  let h = 0x811c9dc5;
  for (let i = 0; i < input.length; i++) {
    h ^= input.charCodeAt(i);
    h = Math.imul(h, 0x01000193);
  }
  return (h >>> 0).toString(16).padStart(8, "0");
}
// contentHash = fnv1a32( normalizeText(el.textContent).slice(0, 32) )
```

These are the live runtime's functions (`studio/hypresent/runtime/js/comments.js`). Reusing its exported `buildAnchorKey(el)` over the parsed DOM is the most reliable path.

## Procedure

1. Pick the target element the comment is about.
2. Compute the `anchor` and `contextText` per above — by computation, never by eye.
3. Read the island; find the highest existing `id`; set the new `id` to that + 1 (`"1"` if empty).
4. Assemble the thread object (schema above) with `resolved: false`, `replies: []`, and `createdAt` = now.
5. Append the object to the island array. Keep the JSON valid — do NOT reformat or touch any other thread.
6. If `agentInstruction` is `true`: add the token `data-hyp-agent="{id}"` to the target element (space-separate it into an existing `data-hyp-agent` attribute if one is present). The head instruction block regenerates from this on the next hypresent save.

## Invariants

| # | Invariant | Rule |
|---|-----------|------|
| 1 | Append only | Add your thread; NEVER edit, reorder, resolve, or delete an existing thread — that is the Comment Implementation Protocol's job. |
| 2 | Compute the anchor | A fabricated `contentHash`/`path` loads the comment `unanchored` and invisible. Compute every anchor field. |
| 3 | Unique id | The new `id` is strictly above every existing `id` in the island. |
| 4 | Own identity | `author` is the agent's `{agent-name} ({role} agent)` identity — so the owner can tell agent-authored comments from human ones. |
| 5 | Version, never overwrite | If you were handed a file to annotate, write the change to a NEW `-vN` copy (highest existing version + 1); the original stays byte-untouched. |
| 6 | Island is the record | The `#hyp-comments` island is authoritative. Do NOT hand-write the head agent block — it regenerates from the island on the next hypresent save. |

## Example

A human-facing note on a `<div class="ftitle">…</div>` inside `<div id="flags">`, appended as the island's 9th thread:

```json
{
  "id": "9",
  "anchor": { "hook": null, "path": "div:1/div:13/div:2", "nativeId": "flags", "contentHash": "1a2b3c4d", "siblingIndex": 0 },
  "contextText": "Manus pricing now confirmed against the leaderboard",
  "author": "Vivian (designer agent)",
  "createdAt": "2026-06-16T22:14:08.001Z",
  "body": "Cross-checked Manus price against the published leaderboard — it matches. Flagging for your sign-off.",
  "resolved": false,
  "replies": [],
  "agentInstruction": false
}
```
