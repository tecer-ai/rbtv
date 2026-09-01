---
id: html-review
description: Produce a Review page of a plan, document, or diagnosis the owner can read and comment on, with yellow and red flags legible at a glance.
inputs: the source being reviewed (required); a brand-pack overlay if one is present; optionally the `visual-check` capability (design component)
outcome: a Review page sits beside the source, commentable, with yellow and red flags legible at a glance
outputs: `{name}.html` as a sibling of the source; `{name}-assets/` only when real binary assets exist; a source-sync note when the HTML is a rendered view of another file
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

The previously installed personal `html-review` command is RETIRED; this file supersedes it. Its substance split: page rules went into the standards library; the remaining invoke-procedure is this file. After `rbtv install`, agents load the skill generated from this component's `exposure.csv` row. NOTHING continues to load the old seed file or the retired personal command copy.
