---
id: write-reference
description: "Author the complete body of the seeded reference piece inside the assigned probe folder, to the one-subject law and the prose law of the guides this task names"
---

<task-goal>
Deliver one complete reference file body for the seeded piece, written to the one-subject law of the guides this task names.
</task-goal>

<scope>
- **Read:** the seeded piece row; the one-subject law and the prose law in the guides named in this task's Guides bullet; the target component's existing reference files, as precedent for its live conventions.
- **Write:** the assigned filename inside the assigned probe folder — nothing else. The target path the piece row names belongs to the dispatching seat.
- **Guides — read whole before writing:** `references/kind-reference.md`; `references/authoring-style.md`.
</scope>

<done-contract>
Done criteria — all must hold:

- A file exists at the assigned filename inside the assigned probe folder, carrying frontmatter and body whole — no placeholder, no section deferred, nothing left for a later hand.
- Its frontmatter carries a `description` naming the MOMENT the file is read rather than merely its contents, plus the `tags` the target component's sibling reference files carry.
- The body carries exactly ONE subject: its description states what the file covers without an "and" joining two subjects, and no section in it is one a reader would reach for without reading the rest.
- Every requirement in the body reads MUST, NEVER, or ALWAYS; every genuine judgment call or hint is marked as one.
- No sentence in the body is deletable without losing a requirement or a judgment call.
- No owner-specific value appears — no channel id, account, host, credential, or workspace path.
- The return `{piece-id, kind, probe-path, self-check: pass|fail, evidence}` reached the dispatcher, its evidence naming, per rule of the named guides, the draft line that satisfies it.

Outcome map:

- **self-check pass** → the dispatching seat re-reads the body and lands it at the piece row's target path.
- **self-check fail** → the return still reaches the dispatcher, naming every failing rule; the seat re-dispatches once or drafts inline. Feedback schema: {piece-id, the rule, the draft line that fails it}.
- **The split test names a second subject** → return `self-check: fail` with the split named; never merge two subjects into one file. Feedback schema: {piece-id, the two subjects, the sentence carrying the "and"}.
- **A sibling already serves the subject** → return `self-check: fail` naming that sibling and the amendment it should take instead; a second home for one fact is never drafted. Feedback schema: {piece-id, the sibling's path, the amendment}.
</done-contract>
