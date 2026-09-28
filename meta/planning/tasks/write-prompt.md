---
id: write-prompt
description: "Author the complete body of the seeded prompt piece inside the assigned probe folder — the exact frontmatter card, the kind-named sections in canonical order, and the ethos carry where the piece row orders one"
---

<task-goal>
Deliver one complete prompt file body for the seeded piece, its card and every section authored to the guides this task names.
</task-goal>

<scope>
- **Read:** the seeded piece row; the prompt-file law, the six section guides, the shared ethos, and the prose law in the files named in this task's Guides bullet; the target component's existing prompt files, as precedent for its live conventions; the target component's `exposure.csv`, to key every declared instrument to the method its row carries.
- **Write:** the assigned filename inside the assigned probe folder — nothing else. The target path the piece row names belongs to the dispatching seat.
- **Guides — read whole before writing:** `references/file-prompt.md`; `references/kind-role.md`; `references/kind-procedure.md`; `references/kind-io-spec.md`; `references/kind-permissions.md`; `references/kind-restrictions.md`; `references/kind-constraints.md`; `references/ethos.md`; `references/authoring-style.md`.
</scope>

<done-contract>
Done criteria — all must hold:

- A file exists at the assigned filename inside the assigned probe folder, carrying frontmatter and every demanded section whole — no placeholder, no section deferred.
- The frontmatter parses as YAML and carries only these fields: `id`, `description`, `staffing-recommendations`, `human-interactive`, `fallback`, `exposes`. `id` equals the assigned filename's stem. `human-interactive` appears only where the seat's ROLE includes reaching the human; `fallback` appears exactly where `human-interactive: yes` does, typed `park`, `default-and-disclose`, or `block-and-queue`; `exposes` appears only where the seat must reach a materialized instrument, each group key agreeing with the method that part's `exposure.csv` row carries.
- Every `exposes:` entry under `path`, `skill`, or `sub-agent` carries its own bullet in `<resources>`, naming the part-id and saying in at most 280 characters how the occupant uses it — when to reach for it, what it hands back, its caveat. Exempt: the `rbtv:ignite/team-kit/coordinate` checkout grant, and every `command`, `rule`, and `hook` entry. Declaration 2 of `references/workflow-authoring-checklist.md` rules it.
- The body carries kind-named XML sections in exactly this order — role → procedure → resources → io-spec → permissions → restrictions → constraints — with role, procedure, io-spec, permissions and restrictions all present, at most one section per kind, and no section outside that set.
- Where `fallback: block-and-queue` is declared, the procedure carries a step opening with the literal marker `Autonomous arm —`, stating what the seat derives, from what, and where it records the derivation and its provenance.
- Where the piece row names this prompt an ethos carrier, its constraints section is opened with the `source` attribute the constraints guide states, carries the ethos block copied byte-identically between its two marker lines, and keeps every carrier-local sentence below the end marker.
- Every requirement reads MUST, NEVER, or ALWAYS; every judgment call is marked as one; no step cites a record the reader would have to look up before acting.
- No harness binding, model binding, version pin, task-serving unit, or run-instance value appears; no owner-specific value appears.
- The return `{piece-id, kind, probe-path, self-check: pass|fail, evidence}` reached the dispatcher, its evidence naming, per rule of the named guides, the draft line that satisfies it.

Outcome map:

- **self-check pass** → the dispatching seat re-reads the body and lands it at the piece row's target path.
- **self-check fail** → the return still reaches the dispatcher, naming every failing rule. Feedback schema: {piece-id, the rule, the draft line that fails it}.
- **An instrument the seat needs has no `exposure.csv` row in its component** → return `self-check: fail` naming the instrument and the row that is missing; never declare a group key no row backs. Feedback schema: {piece-id, the instrument, the method its row would carry}.
- **The pool already holds a prompt an existing seat could reuse** → return `self-check: fail` naming that prompt; two prompts whose honest personas converge are one prompt. Feedback schema: {piece-id, the existing prompt's path, the converging persona}.
</done-contract>
