---
name: rbtv-hypresent-comments
description: "Add, review, answer, implement, resolve, annotate, read, search, or strip REVIEW comments on an HTML artifact (a page, deck, presentation, dashboard, or mockup) — the hypresent comment system. Use WHENEVER a user asks to: 'add comments to an HTML', leave review notes / feedback / annotations on an HTML, comment on a page/deck/mockup; OR review / read / go through / respond to / answer / address / resolve / implement the comments in an HTML — even when the user never says the word 'hypresent'. ALSO fires on deck-query intents — 'what does this deck / section / slide / comment say', read / inspect / search / summarize a hypresent HTML file or its comments (route to the browser-free `hypresent.py read` / `search` subcommands, which answer without reading the whole file) — and on comment-removal intents — 'strip / remove / delete the comments' on a hypresent deck (route to `hypresent.py delete-comment`; DESTRUCTIVE and owner-directed only — an agent never deletes or resolves a human's threads on its own initiative). In ALL these cases route through this skill and the file's #hyp-comments island; NEVER leave review notes as raw HTML `<!-- -->` comments (they are invisible in hypresent). Modes: RESPOND to existing comments (apply each change, reply inline under the agent's own identity, never resolve the human's thread), AUTHOR a new comment from scratch (append an anchored thread), or READ / SEARCH / STRIP a deck and its comments. Excludes literal code/markup comments that explain the code itself. Keeps every agent change auditable by the owner."
---

# Hypresent Comments

**CRITICAL — Load the ONE matching procedure file FULLY and follow it EXACTLY before touching any comment. Load only the branch your task needs; do NOT read the other.**

| Your task | Load and follow |
|-----------|-----------------|
| RESPOND to / implement / resolve EXISTING comments | `{rbtv_path}/studio/workflows/hypresent-comments/comment-implementation.md` |
| CREATE a new comment from scratch (your own note, annotation, question, or agent-instruction) | `{rbtv_path}/studio/workflows/hypresent-comments/comment-authoring.md` |

**A review note left as a raw HTML comment (`<!-- … -->`) does NOT work — it never appears in hypresent.** Every hypresent comment is a thread in the file's `#hyp-comments` island; to leave one, follow the authoring branch above.

## Query or strip a deck — run the CLI directly

These intents need NO procedure file — run the browser-free subcommand and answer. Grepping or reading the raw deck HTML is the FALLBACK, never the default. `{rbtv_path}` resolves from `rbtv.json` and is recorded relative to the workspace root: run every `hypresent.py` command with the shell's CWD at the workspace root, or expand the script path and `--file` to absolute paths first.

| Your task | Run |
|-----------|-----|
| READ / inspect the comment set, a thread, or an element; ask what a deck / section / slide / comment SAYS | `python {rbtv_path}/studio/hypresent/tools/hypresent.py read --file <deck.html>` (add `--comment <id>` + any combination of `--self`/`--parent`/`--sibling` for one thread's element context, or `--selector "<css>"` for a one-off element read) |
| SEARCH / locate content in a deck | `python {rbtv_path}/studio/hypresent/tools/hypresent.py search --file <deck.html> --query "<term>"` |
| STRIP / remove / delete comments — DESTRUCTIVE, owner-directed ONLY | `python {rbtv_path}/studio/hypresent/tools/hypresent.py delete-comment --file <deck.html> (--comment-id <id> | --all) [--out <new.html>]` |

Deletion is destructive: run `delete-comment` ONLY on the owner's explicit instruction. An agent NEVER deletes or resolves a human's threads on its own initiative — the comment thread is the human's record.
