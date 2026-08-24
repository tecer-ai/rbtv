---
description: "Read at the moment a change leaves code unused — after an edit, a fix, or a refactor — to rule what is deleted: everything your change made unreachable, and never a commented-out or kept-for-later remnant."
tags: [coding]
---

# no-dead-code

Code is ALWAYS left clean: after your change, nothing remains that your change made unused.

## What counts as dead

A function, method, class, variable, import, parameter, file, config key, CLI flag, branch, or test that nothing reaches after your change. This includes: the old code path a fix replaced; the helper only the deleted code called; the import only the deleted line used; the flag only the removed branch read; commented-out code of any age; a block kept "for later".

## Rules

| # | Rule |
|---|------|
| 1 | After every change, you MUST trace what it made unreachable — follow the callers and readers of everything you removed or rewrote — and DELETE it in the same change. |
| 2 | NEVER comment code out, and NEVER keep a block "in case". Version control is the archive: a deleted thing is recovered from history if a need ever arrives. |
| 3 | The ONLY exemption: a public interface you can VERIFY is consumed outside this codebase (a published CLI verb, a served endpoint, a library export with an external caller). "Might be used somewhere" is not verification — grep the consumers; unverifiable → delete. |
| 4 | Dead code you find that your change did NOT make dead is pre-existing: name it (file, symbol) in your closing message; NEVER delete it unasked. |

## Tripwire

Before closing a change, for every symbol you removed or rewrote, answer: what else existed only for it? That list is what you delete.
