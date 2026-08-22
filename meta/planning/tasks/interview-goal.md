---
id: interview-goal
description: "Interview the owner from goal seed to a ratified goal.md carrying the goal and a falsifiable definition of done"
---

<task-goal>
Interview the owner from the seeded planning request to a ratified `goal.md` — the goal plus a definition of done falsifiable in every clause.
</task-goal>

<scope>
- **Read:** the goal seed and every artifact it names (the subject workflow of an optimize ask, the foreign process artifact of a port, prior notes); the owner's answers on the goal's owner-channel thread.
- **Write:** `goal.md` in the goal folder.
</scope>

<done-contract>
Done criteria — all must hold:

- `goal.md` exists in the goal folder and carries three named parts: the goal statement, the definition of done, and the ratification record (the owner's explicit ratifying answer, quoted or linked).
- Every definition-of-done clause names an observable, the probe that checks it, and its threshold — no clause left that two readers could score differently.
- Every question raised to the owner is either answered and folded in, or still queued on the owner-channel thread — none dropped.
- Where the request produces a WORKFLOW into the scaffolding (`use-case:` optimize, port, or scaffold), `goal.md` carries `default-execution-mode:` — `interactive` or `autonomous` — as the owner confirmed it, this being the default a goal created from that workflow will be born with (owner ruling 2026-08-10). An `ad-hoc` request produces no workflow and carries no such field; its absence there is correct, not missing.
- Where the request produces a WORKFLOW into the scaffolding (`use-case:` optimize, port, or scaffold), `goal.md` carries TWO ratified user stories — one for human exposure, one for agent exposure — and each is served by at least one definition-of-done clause. An `ad-hoc` request carries neither; their absence there is correct, not missing.

Outcome map:

- **Complete** → `goal.md` seeds the split step.
- **Owner answers pending** → the task WAITS LOUDLY: questions and draft parked on the coordination bus addressed to the reserved `owner` token — a disclosed waiting state, never a silent stall — and it never completes on an unratified definition of done (the ONE sanctioned hard gate; a seed carrying an owner-ratified DoD skips the wait entirely). Feedback schema: the queued questions, each paired with the definition-of-done clause it blocks.
- **Owner rejects the draft** → revise and re-present. Feedback schema: the owner's objection paired with the clause(s) it touches.
</done-contract>
