---
description: Author one reusable component prompt file and its frontmatter card
tags: [planning]
---

# Prompt file — `prompts/<id>.md`

A reusable prompt defines the occupant's HOW. Pair it with a task through the owning
component's `seats.csv`; a console seat plan instead writes the whole job in `seat.md`.
Check the component's existing prompts before creating another role with the same job.

The file name and frontmatter `id` match. Its `description` tells a reader when to use it.
`staffing-recommendations` may offer a hint without binding a model. `exposes` names any
independently exposed skill, sub-agent, or path the prompt uses; each must resolve in an
`exposure.csv` row. Describe why and when each is used in `<resources>`. Keep instance paths,
credentials, and owner identities out of the source file.

**Body — one kind-named XML section per unit, in this order:**

`<role>` → `<procedure>` → `<resources>` → `<io-spec>` → `<permissions>` → `<restrictions>` → `<constraints>`

`<role>`, `<procedure>`, `<io-spec>`, `<permissions>`, and `<restrictions>` are required.
`<resources>` exists when a procedure uses an instrument; `<constraints>` exists when a
judgment-bound rule is needed. Author each section with its matching `kind-*.md` guide.
The prompt states the method; its paired task states the aim, scope, and done contract.

Before registering it, check that a stranger could follow the procedure with the named inputs
and instruments, that every declared instrument has a real step, and that the paired task's
result can be verified. Run `component-lint` on the owning component.
