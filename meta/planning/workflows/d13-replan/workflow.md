---
name: d13-replan
default-execution-mode: interactive
four-letters: repl
---

# d13-replan — the workflow

**Four letters (`repl`).** The prefix every seat-id in `d13-replan.csv` shares
(`repl-understander`, `repl-drafter`, `repl-verifier`) — mechanically required by the bindings
capability's `workflow_code()`, which REFUSES a manifest whose rows share no single prefix, and any
prefix that is not exactly four ASCII LETTERS. `d13` is not a legal code (digits), so the workflow
FOLDER carries the D13 name and the SEAT ids carry `repl`; the code owes nothing to the workflow's
name (precedent: workflow `plan-console`, seats `plan-*`). It names this workflow's casting sheet
(`.rbtv/config/modules/meta/planning/bindings/repl.json`) and is the prefix these seats carry
inside the goal they are minted into.

**Default execution mode.** `interactive` — declared above. It is the value a goal created from
this workflow is BORN with. D13 seats are minted into an EXISTING execution goal, which already
carries its own `execution-mode`; that goal's value governs, and this declaration is the floor for
the case where the workflow is ever opened on its own. Every row below carries Modality
`interactive`, so derivation would reach the same answer; the declaration is what lets a later
owner ruling say otherwise without rewriting the manifest.

**Goal.** Close a gate failure without stopping the goal. A milestone's closing judge returns FAIL;
this workflow understands why, patches that milestone's plan and seats to cover the gap, checks the
patch against the milestone's UNCHANGED done contract, and hands back a milestone that can re-run.
The owner is notified on Slack and intervenes only by choice — until the cap below. [D13]

**Scope.** Three seats, one linear pass: understand → draft → verify. There is NO design stage and
NO review stage — the approach is not open (the milestone's contract is frozen) and there is
nothing to review that verify does not already check. [D13, T3-R9] Each seat may ask the owner;
none has an ask-cap and none has a wall-clock deadline (the only clock is the daemon's shared
~30-min no-progress kill). [T3-R13, T3-R18, CF-1, D24]

**Reuse, not a second pipeline.** All three seats REUSE the main planning pipeline's prompt
definitions — `understander`, `drafter`, `verifier`. What is D13-specific is the TASK each is
paired with: `gap-understand` (the combined understand: gate verdict + what execution produced),
`patch-draft` (the patch), and `verify-patch` (the notify-only check). [T3-R9, T3-R16]

**Why verify has its own task (owner ruling 2026-08-25).** The verify seat used to reuse
`verify-plan` as written, on the grounds that its check (b) — every milestone id still present with
its done-criteria unbroken — IS the unchanged-contract check D13 needs. The check was right and the
CONTRACT around it was wrong in kind: `verify-plan` issues a FAIL verdict that re-fires the drafter
and withholds its product until a cap is reached, and it composes a plan-APPROVAL digest offering
`approve` / `reject-close` / `reject-pause` / `reject-retry`. Both of those are GATES, and this lane
does not gate — its baseline behaviour is to continue autonomously and notify [D13]. So D13 owns its
own verify task. `verify-patch` runs the same unchanged-contract check, adds the two patch walls as
its second check, and its product is a NOTICE, not a digest and not a verdict.

**Where it runs, and how it is minted.** Inside the EXISTING execution goal, on the same milestone
— no new goal is created. The mint is path A of the supervised materialize wrapper (same-goal
atomic seat mint), the SAME door the plan-approval create-and-start uses; D13 invents no second
door and this workflow implements no mint of its own. [CF-11, D13, spec-planning-door §2.3] The
failure arm of that wrapper — the gate lane stamped `incomplete: materialize-failed` — belongs to
the door, not to this workflow. [C-16]

**Procedure (`d13-replan.csv` is the whole DAG — three rows, linear, no forks, no guards).**

1. `repl-understander` (prompt `understander` + task `gap-understand`) — reads the gate verdict,
   the milestone's done contract as written, that milestone's plan and seats, and every artifact
   those seats declared at its declared path. Writes `planning/replan/gap-brief.md`: the verdict,
   what execution actually produced, the gap clause by clause, the salvage inventory, and one
   explicit BOUNDARY CALL — `contained` or `cross-milestone`. Understand and "what execution
   produced" are ONE stage here, not two. It proposes no patch.
2. `repl-drafter` (prompt `drafter` + task `patch-draft`) — reads the gap brief and writes
   `planning/replan/patch-plan.md`, whose second line is `disposition: patch` or
   `disposition: escalate`. Two walls bind the patch, and they are the whole reason this stage is
   narrower than the main pipeline's draft: it may amend ONLY the failed milestone's plan and
   seats, and it MUST NOT widen the permission envelope. A gap that crosses milestone boundaries —
   or that needs one more grant — is NOT patched: the seat escalates to the owner with its
   analysis and zero patch content. [T3-R19]
3. `repl-verifier` (prompt `verifier` + task `verify-patch`) — runs two checks against the patch:
   the milestone's contract is UNCHANGED, and the patch stayed inside `patch-draft`'s two walls.
   Writes `planning/replan/replan-notice.md`, whose second line is `check: pass` or
   `check: problems`, and sends it once to the owner. It never parses a reply.

**There is no regression loop, and that is the ruling's load-bearing word — NOTIFY-ONLY.** No seat
in this workflow declares an `on-fail-relaunch` entry, so `coord`'s loop re-fire
(`on_fail_relaunch_route`, which reads that frontmatter key off the issuing seat's own `seat.md`)
resolves to the empty route and re-dispatches nothing. `repl-verifier` issues no verdict either:
the verdict verb is the ONE door that arms the escalation gate, and an armed gate halts the
milestone's contract until the owner answers. A problem `verify-patch` finds is therefore written
into the notice, sent once, and the replan finishes anyway — the milestone re-runs and the owner
intervenes only by choice. Nothing here is withheld, capped or counted; the only cap in D13 is the
daemon's, below.

**The two-failed-replan cap — DAEMON policy, documented here, implemented nowhere in this
workflow.** After TWO failed re-plans of the SAME milestone, the daemon stops replanning it: there
is no third. A Slack decision-ask opens carrying both gate verdicts and both patch plans; ONLY that
milestone's lane is stamped `incomplete:` and stops, and every independent lane continues
unaffected — a whole-goal skip is a defect, not the design. [T3-R11, CF-10, D16] The counter lives
with the daemon, is derived from the milestone's verdict history, and is NOT stored, declared or
counted by any seat in this workflow. A seat here can neither know nor enforce it, and must not try:
each firing of this workflow is one replan attempt and behaves identically whether it is the first
or the second.

**Envelope, credentials, scaffolding.** This workflow compiles no envelope and mints no durable
scaffolding. The patch runs inside the execution goal's already-compiled envelope; the envelope
compiler and its launch-refused stamp are the envelope component's. The digest names credential
NAMES only, never values.

**The patched seats run synchronously.** A seat `patch-draft` amends runs HEADLESS: its sitting lasts exactly one turn, so patch text that tells an occupant to background a check or wait for a notification orphans that occupant's work behind an exit-0 stub report. `repl-drafter` MUST write every amended seat body to run its checks in the foreground and scope a slow check DOWN rather than defer it. The failure and its recovery: `references/headless-seat-cannot-wait.md`.

**Inadequate input, any stage.** Repair the gap yourself, log it in `input-gaps` and the goal's
`decisions.md` (or `doubts.md` if unclosable), and continue. No stage re-entry, no rejection
verdict, and no re-run of the milestone's own seats from inside this workflow. [T3-R8, D11]

**Next-stage launch** is the ordinary task-graph `after` edge — no splice, no new mechanism. The
retired per-milestone splice that the old system replanned through does not run here and is not
teaching to copy. [CF-11, D9, D10]

**Artifacts.** Both D13-specific artifacts land under `planning/` in the goal folder — the one
subtree the cage opens read-write to every seat — at `planning/replan/`, each with a first-line
marker its consumer checks (`GAP-BRIEF`, `PATCH-PLAN`). `planning/current/` is NOT written by this
workflow: it is the planning door's locked, derived tree.
