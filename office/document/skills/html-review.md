---
name: html-review
description: "Reviews produced HTML output against the standards library."
---

# html-review

Agent-authored HTML. Page-type: Review. Load `html-standards` as the single load point; NEVER load a library sibling directly; NEVER restate what the library carries.

## Procedure
1. Load `html-standards`.
2. Write the page against the Review profile.
3. Stop.

## Missing brand pack

A missing brand pack is non-halting. Fallback to the library's shipped design-system default and keep running. Review MUST still produce a page.

## Supersession

The previously installed personal `html-review` command is RETIRED; this file supersedes it. Its substance split: page rules went into the standards library; the remaining invoke-procedure is this file. After `rbtv add`, agents load the skill generated from this component's `exposure.csv` row. NOTHING continues to load the old seed file or the retired personal command copy.
