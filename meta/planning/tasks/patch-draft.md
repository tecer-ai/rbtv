---
id: patch-draft
description: "Patch the failed milestone's plan and seats to cover the gap — same milestone only, envelope unwidened, or escalate with the analysis instead"
---

<task-goal>
Turn the seeded gap brief into a patch that covers the gap: the failed milestone's plan and seats
amended so the milestone's UNCHANGED done contract can be met on a re-run. Where the gap brief's
boundary call is `cross-milestone`, produce the escalation analysis instead of a patch — the two
outcomes are the same product file, distinguished by its disposition line.
</task-goal>

<scope>
- **Read:** `planning/replan/gap-brief.md`; the failed milestone's plan and its seats; that
  milestone's done contract, as written and unchanged; the goal's compiled permission envelope;
  every salvage artifact the gap brief inventories; owner replies on the goal channel.
- **Write:** `planning/replan/patch-plan.md`.
</scope>

<done-contract>
Done criteria — all must hold:

- `planning/replan/patch-plan.md` exists and its first line is exactly `PATCH-PLAN`.
- The second line is exactly `disposition: patch` or `disposition: escalate`, and it agrees with
  the gap brief's boundary call — `contained` → `patch`, `cross-milestone` → `escalate`. A
  disposition that contradicts the boundary call is a fail; disagreeing with the call is done by
  correcting the call in this file's `input-gaps` with the evidence, never by silently flipping the
  disposition.

Under `disposition: patch`, additionally — each of the first two is a WALL, and a patch that
crosses either is a fail, not a variant:

- **WALL — one milestone.** Only the failed milestone's plan and seats are amended. No other
  milestone id appears in the patch as added, removed, re-scoped, re-edged or re-staffed; no
  milestone's done contract is changed, including this one's. The patched milestone's done contract
  is quoted VERBATIM in the file as the contract the patch is built to meet.
- **WALL — no envelope widening.** The patch adds no bind, no path, no host, no tool, no credential
  name and no grant that the goal's compiled envelope does not already carry, and removes no
  restriction it does carry. The file states, in one line per patched or added seat, that the seat
  runs inside the existing envelope, naming the grants it uses. A patch that needs one more grant
  is not a patch — it is the `escalate` disposition.
- Every failed clause named in the gap brief is paired with the patch element that closes it, and
  no failed clause is left unpaired.
- Every seat the patch adds or amends carries the six authoring declarations: its ONE `goal-writes`
  path or a documented empty column plus a `chat` schema; every instrument declared and described;
  `human-interactive` plus a typed `fallback` where the role reaches the human; the fixed
  seat-folder names; no hardcoded owner value; a complete, machine-checkable done contract.
- No seat the patch adds or amends carries a wall-clock deadline field and none carries an ask-cap.
- Salvage is honoured: an artifact the gap brief inventoried as still-proving is reused, not
  re-derived by a new seat.

Under `disposition: escalate`, additionally:

- The file carries analysis ONLY. No patch, no amended seat, no new edge, no grant — zero patch
  content, so that nothing here can be materialized by mistake.
- The analysis names: which failed clause forces the crossing, which other milestone or which
  envelope grant it reaches into, what a correct fix would have to change, and the options the
  owner is being asked to choose between.

In both dispositions:

- An `input-gaps` list is present (may be empty).
- No credential *value*, owner-specific channel, host, account, or vault path appears in the file.
- Completeness: every failed clause has a closing patch element or an escalation reason; every seat
  the patch names exists in the milestone or is declared as added; two seats with the same id is a
  fail; a declared output present in neither a seat's `goal-writes` nor a named handoff is a fail;
  a patch element closing a clause the verdict never failed is reported as scope beyond the gap and
  removed.

Outcome map:

- **`disposition: patch`** → the patch seeds the verify stage, which checks it against the
  milestone's unchanged contract.
- **`disposition: escalate`** → the analysis seeds the verify stage too; verify checks that the
  file carries no patch content and that the crossing is named. The escalation reaches the owner
  through the goal's ordinary owner-contact path, not by this task posting.
- **Markerless or thin gap brief** → repair forward from the verdict and what is on disk, log the
  gap, complete. Never reject. Never re-enter the understand stage.
- **A fix pass relaunched by the verify seat** → treat the failed check's items as the only fix
  targets; do not reopen the patch beyond them, and do not widen the milestone.
</done-contract>
