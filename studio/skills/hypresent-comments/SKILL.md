---
name: rbtv-hypresent-comments
description: "Add, review, answer, implement, resolve, or annotate REVIEW comments on an HTML artifact (a page, deck, presentation, dashboard, or mockup) — the hypresent comment system. Use WHENEVER a user asks to: 'add comments to an HTML', leave review notes / feedback / annotations on an HTML, comment on a page/deck/mockup; OR review / read / go through / respond to / answer / address / resolve / implement the comments in an HTML — even when the user never says the word 'hypresent'. In ALL these cases route through this skill and the file's #hyp-comments island; NEVER leave review notes as raw HTML `<!-- -->` comments (they are invisible in hypresent). Two modes: RESPOND to existing comments (apply each change, reply inline under the agent's own identity, never resolve the human's thread) or AUTHOR a new comment from scratch (append an anchored thread). Excludes literal code/markup comments that explain the code itself. Keeps every agent change auditable by the owner."
---

# Hypresent Comments

**CRITICAL — Load the ONE matching procedure file FULLY and follow it EXACTLY before touching any comment. Load only the branch your task needs; do NOT read the other.**

| Your task | Load and follow |
|-----------|-----------------|
| RESPOND to / implement / resolve EXISTING comments | `{rbtv_path}/studio/workflows/hypresent-comments/comment-implementation.md` |
| CREATE a new comment from scratch (your own note, annotation, question, or agent-instruction) | `{rbtv_path}/studio/workflows/hypresent-comments/comment-authoring.md` |

**A review note left as a raw HTML comment (`<!-- … -->`) does NOT work — it never appears in hypresent.** Every hypresent comment is a thread in the file's `#hyp-comments` island; to leave one, follow the authoring branch above.
