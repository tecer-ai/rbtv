---
description: Author one reusable component task file and its frontmatter card
tags: [planning]
---

# Task file — `tasks/<id>.md`

A reusable task defines the seat's WHAT. Pair it with a prompt through the owning component's
`seats.csv`; a console seat plan instead writes the whole job in `seat.md`. Name the task for
its action, such as `review-build`, not for the workflow that happens to use it. The file name
and frontmatter `id` match; `description` is a one-line reader-facing summary.

**Body — one kind-named XML section per unit, in this order:**

`<task-goal>` → `<scope>` → `<done-contract>`

All three are required. The goal states the result, scope names what the task reads or writes,
and the done contract names checks a consumer can reproduce. Use the matching `kind-*.md`
guide for each. Runtime inputs arrive with the seat request; do not bake one owner's paths,
credentials, or project names into the reusable task. Tools belong in the paired prompt's
`<resources>` and exposure declarations, not in a `capabilities:` or `context:` field here.

Check that the task is bounded, its inputs are supplied, and the done contract covers failures
and duplicates as well as the happy path. Run `component-lint` on the owning component.
