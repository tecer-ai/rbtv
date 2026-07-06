# Comment Authoring Protocol

The MANDATORY protocol ANY agent follows to CREATE a new hypresent review comment from scratch — its own review note, question, or an instruction for a coding agent. You author a comment by invoking ONE tool with a CSS selector and the comment text. The tool drives the real hypresent runtime to compute the anchor and write a valid file. You NEVER hand-edit comment data, compute an anchor, or read runtime code.

> **A hypresent comment is NOT an HTML comment.** A raw HTML comment — `<!-- … -->` — is INVISIBLE in hypresent: no marker, no thread, no anchor, and the owner never sees it in the review UI. NEVER leave a review note, change request, or instruction as `<!-- … -->`.

## Confirm Intent First — MANDATORY

"Add a comment" is ambiguous. Before authoring ANYTHING, CONFIRM with the user which kind they want — the two are different things with different visibility:

| Kind | What it is | Visible where |
|------|-----------|---------------|
| Hypresent review comment | An anchored thread in the deck's comment data — THIS protocol | In the hypresent review UI (marker + thread); the owner can reply/resolve |
| Raw HTML comment (`<!-- … -->`) | A plain markup comment in the source | ONLY in the raw file source — INVISIBLE in hypresent |

Ask the user, and proceed with this protocol ONLY on a hypresent answer:

> Do you want a **hypresent review comment** (shows up in the review UI for you to resolve) or a **plain HTML source comment** (`<!-- … -->`, only visible in the raw file)?

If the user wants a raw HTML comment, this protocol does NOT apply — add the `<!-- … -->` directly and stop here. Proceed below ONLY for a hypresent comment.

## Inspect the deck FIRST — read / search

To see the existing comment set, a specific thread, an element, or to locate content before authoring, run the browser-free reader FIRST — it answers without loading the whole deck. `{rbtv_path}` resolves from `rbtv.json` and is recorded relative to the workspace root: run EVERY `hypresent.py` command in this protocol with the shell's CWD at the workspace root, or expand the script path and `--file` to absolute paths first — a bare relative invocation from any other directory fails to find the script.

```
python {rbtv_path}/studio/hypresent/tools/hypresent.py read --file <deck.html> --selector "<css>"
python {rbtv_path}/studio/hypresent/tools/hypresent.py search --file <deck.html> --query "<term>"
```

`read` prints the comment threads (default), or an element by `--selector "<css>"`, or one thread's element by `--comment <id>` with any combination of `--self`/`--parent`/`--sibling` (one call returns the union of the requested contexts); `search` finds page text and returns located snippets. Grepping or reading the raw deck HTML — or generating a lean view for a mere question — is the FALLBACK, not the default. Generate a lean view (below) only for a whole-deck scan or a token-reduced full read.

## How to Author — invoke the tool

Run ONE command (CWD at the workspace root, per the Inspect section above):

```
python {rbtv_path}/studio/hypresent/tools/hypresent.py add-comment \
  --file <deck.html> \
  --selector "<unique CSS selector for the element to comment on>" \
  --body "<the comment text>" \
  --author "{agent-name} ({role} agent)" \
  [--agent] [--out <new.html>]
```

| Arg | Meaning |
|-----|---------|
| `--file` | The HTML deck. MUST be a conforming hypresent deck — built from `<section>` slides. |
| `--selector` | A CSS selector matching EXACTLY ONE element — the element the comment is about. If it matches 0 or >1, the tool refuses; make it more specific (scope by a section id, e.g. `#screen-overview .screen-title`). |
| `--body` | The comment text — your note, question, or instruction. |
| `--author` | Your OWN identity, `{agent-name} ({role} agent)` — so the owner can tell agent comments from human ones. |
| `--agent` | The action gate. Include ONLY when a coding agent should act on the comment (adds the agent-instruction tag + head block). Omit for a human-facing note or question — a comment authored WITHOUT `--agent` is informational only: agents IGNORE its content (never act on it) but always preserve it and keep it anchored. To make a comment actionable by an agent, you MUST pass `--agent`. |
| `--out` | Optional. Write to a NEW file instead of overwriting `--file`. Use this when you were handed a file to annotate (version, never overwrite). |

The tool selects the element, adds the comment through the real comment UI (the runtime computes the anchor), confirms a visible marker rendered, and saves a valid file. It handles elements inside hidden / inactive screens of a multi-screen deck automatically (it navigates to the screen before commenting and restores the original screen visibility on save) — so target the exact element regardless of which screen is currently shown. On success it prints `ok`, the new `comment_id`, the computed `anchor`, and `marker_rendered: true`. A non-unique selector, a non-commentable element, or an unanchored result each fails LOUDLY with a clear message — fix the selector and re-run. The retired wrapper's `add_comment: ERROR —` prefix is now `hypresent add-comment: ERROR —`; consumers grepping the old prefix must update.

## Find the target without reading the whole deck

A large deck is expensive to read in full just to pick the element and craft a unique `--selector`. Generate a token-reduced read view first:

```
python {rbtv_path}/studio/hypresent/tools/hypresent.py dehydrate --file <deck.html>
```

It writes `<deck>.lean.html` — the deck with its visual layer (CSS, inline SVG, fonts, vendor JS) stripped, every `id`/`class`/section kept, led by a lossless digest of existing comments. The lean view does not carry the raw `#hyp-comments` island unless the sanctioned never-grow fallback emits the source verbatim and reports `fallback: true`. Read the lean view, pick the element, and craft `--selector` from it: any selector that resolves in the lean view resolves in the real deck, so `hypresent.py add-comment` anchors it unchanged. When the comment is ABOUT a visual property (color, type, spacing, layout), first read the full styling of the target — the lean view omits visual state. Use `python {rbtv_path}/studio/hypresent/tools/hypresent.py read --file <deck.html> --selector "<css>"` for an ephemeral read of elements not already tagged by a comment; commented elements resolve by literal `data-hyp-cid`.

## Pin precisely — one comment per element

| Rule | Detail |
|------|--------|
| Pin to the EXACT element | Choose `--selector` for the smallest, most-specific element the comment is about — the heading, the cell, the button, the paragraph — NEVER a broad ancestor (a whole `<section>`, a big wrapper). The marker and thread MUST sit on exactly what the feedback concerns, so the owner sees each comment on the right thing and resolves it in place. If the precise element needs a scoped selector to be unique, scope it (e.g. `#screen-overview .screen-title`) — do NOT retreat to a broader element just to satisfy uniqueness. |
| One element, one comment | NEVER bundle feedback about different elements into a single comment. Each distinct element — and each distinct point — gets its OWN `hypresent.py add-comment` run with its OWN `--selector`. To comment on N elements, invoke the tool N times. |

## Never do these

| Never | Why |
|-------|-----|
| Hand-edit the `#hyp-comments` island or write an anchor yourself | The anchor is computed by the runtime; a hand-written one loads `unanchored` (invisible). A hand-written island can also be unparseable, hiding ALL comments. The tool exists so you never do this. |
| Pin a comment to a broad ancestor, or pack notes about several elements into one comment | The owner can't tell which element each point refers to, and resolving one point can't resolve the others. Pin to the exact element; one element per comment. |
| Read `comments.js` or any runtime file to "understand how it works" | You do not need to. Pass a selector + text to the tool — it owns all of the apparatus. |
| Leave a review note as a raw HTML comment (`<!-- … -->`) | Invisible in hypresent — no marker, no thread. |
| Proceed when the tool cannot run (file is not a `<section>` deck, or Playwright is unavailable) | STOP and tell the user. Do NOT fall back to hand-editing — that reintroduces the invisibility and parse risks the tool removes. |
