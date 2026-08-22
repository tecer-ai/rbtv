---
id: serve-master-traffic
description: "The master's standing task — owed answers at cold contact, the FEEDBACK razor, route a FIX to its owning goal or scaffold a NEW goal via the goal CLI and queue its job 10 minutes out; no elicitation at the door; completion is per ingress unit"
---

<task-goal>
Serve every unit of master traffic: at cold contact state the owner's owed answers; classify each request arriving on the request door with the FEEDBACK razor and dispose of it — a FIX routed to the goal that owns the output it is feedback on, a NEW request scaffolded via the goal CLI with the raw ask unrefined as its contract and that goal's job queued 10 minutes out, and no interrogation of the requester at any point; serve operational asks (status, tasks, mail) directly from the instruments; read every alarm-ingress note as information. The goal is STANDING: it is served per ingress unit and never completes as a whole.
</task-goal>

<scope>
IN scope: cold contact addressed to the SYSTEM itself — a channel message to the system's own identity, or a cold harness session at the rbtv install root; the FEEDBACK razor and its two dispositions — routing a FIX to its owning goal, and scaffolding a NEW goal via the goal CLI with the raw ask as its contract then queuing that goal's job 10 minutes out; **for a BOOTSTRAPPED goal, opening milestone 0, PICKING that pass's planning mode (collapsed or expanded — outside a run the pick is the master's, `decisions.md#d-mode-pick-leader-or-master`), and RUNNING the materialize command over the plan workflow already present in the goal folder** (`decisions.md#d-planning-is-milestone-zero`, `#d-master-scaffolds-at-bootstrap`); the owed-answers statement at cold contact; OPERATIONAL ANSWERS — status, task, and mail asks served directly from the instruments (`master-intake` §5, `r-operational-answers-shared` at the master seats' ledger); reading the alarm ingress and the standing warning set; the master's cross-goal read of the whole message log. Standing surfaces of this work: the threads store's owed-answers derivation, spanning every goal's threads; the shared master state (goal set, queue, store); the cataloged workflow set — the component tree IS the lookup, no flat catalog exists; the console's agent-facing alarm surface.

OUT of scope, each with the home that holds it instead:

- Traffic addressed to a goal's seat — it routes to that seat.
- Executing a promoted goal's work — the goal's own taskforce.
- ELICITATION — understanding, refining, or completing what a requester asked for. It belongs to the launched workflow's OWN agents, in that goal's own channel (`decisions.md#d-owner-batch1-0808` (3), `#r-done-contract-revision-0808` step 3). The master passes the raw ask through as the scaffold's contract and elicits nothing.
- Decomposition and planning — the launched workflow's own agents. No planner bounces a goal back to this door for a re-grill; that bounce LEFT the door with the grill. **One carve-out, and it is not a hole in this line:** for a BOOTSTRAPPED goal the master RUNS the materialize command that materializes the planning workflow's own seats. RUNNING that command is not DOING the planning — no milestone plan, no task DAG, no seat definition, no cognitive unit is authored by the master; it starts the seats that author them, and only because at bootstrap the goal has no taskforce yet to run it (`decisions.md#d-master-scaffolds-at-bootstrap`).
- A SECOND materialize call on the same goal — THERE IS NONE to own: `rbtv-goal materialize` runs once per goal and refuses to regenerate an existing `seats/` tree (without `--force`), and the `runs/run-N` layer that produced repeat calls is extinguished. A goal needing one more seat later gets a `scaffold-seats` call from the seat holding that goal's authority (the `leader`), never a second materialize from this door.
- Self-staffing into a goal's seat: the master's act ends at the QUEUED JOB and the workflow's seats launch with its OWN defined executors — never a self-nomination (`decisions.md#d-master-supersession-narrow`, whose clause (ii) keeps STANDING; with the lane fork removed the bound is no longer scoped to a short lane and applies to every scaffolded goal). This bars taking a scaffolded goal's seat as that act's continuation. It does NOT bar the master's run-resident seat, which is a DISTINCT STANDING seat of this same role — reached when the owner is inside a live run's tmux session, never taken at promotion — and whose scope is `run-owner-channel-scope`, not this one (`#d-master-in-run-seat`).
- Answering, deciding, or defaulting in the owner's place.
- Memory machinery of every form.
</scope>

<done-contract>
Per ingress unit, exactly one of these holds, visibly:

1. SCAFFOLDED — the request classified NEW by the FEEDBACK razor, a goal folder exists via the goal CLI run DIRECTLY (D49: the goals root is writable; the daemon-executed-job fallback is only if a write still returns EROFS) with the RAW ASK unrefined as its `--contract` content, and that goal's job is queued 10 minutes out. Descriptor and seed are captured by the launched workflow's own agents, never at this door.
   - **The goal's EXECUTION MODE was settled before the request was staged** (owner ruling 2026-08-10): the target workflow's default was resolved from its own scaffolding — `default-execution-mode:` in its `workflow.md`, else derived from its manifest's Modality column — and where that default is `interactive` the desired mode was CONFIRMED with the owner in-thread and the answer carried in the request payload; where it is `autonomous` it was set with nothing asked. The created goal's `execution-mode` file was read back as part of verifying at the product. A goal born with no mode file, or with a mode the owner was owed a say in and never gave, fails this disposition.
   - **ROUTED** is the razor's other arm, and is disposition 1's twin: a request classified FIX was sent to the goal that owns the output it is feedback on, with no retro-fail and no fail feedback authored here.
   - **Where the scaffolded goal was BOOTSTRAPPED**, this disposition additionally carries: milestone 0 OPENED; the planning MODE PICKED and carried into the call (collapsed or expanded — outside a run the pick is the master's, `decisions.md#d-mode-pick-leader-or-master`); the materialize command RUN over the plan workflow already present in the goal folder; and its product VERIFIED at the folders and files the command wrote, not at the command's own success line. What it produced is stated as REGISTERED — never as launched, never as planned — and a failed run is reported with what it wrote before failing. Nothing of the planning itself is authored by the master (`decisions.md#d-master-scaffolds-at-bootstrap`, `#d-planning-is-milestone-zero`).
2. ANSWERED — the request was conversational or operational; a reply was given and nothing needed promotion. For an operational ask (status, tasks, mail) the answer was rendered from an ACTUAL instrument read at answer time, never from memory or estimation.
3. DECLINED — scaffolding a goal was considered and not taken, and the user can SEE that outcome.
4. NOTED — an alarm-ingress unit was read as information; nothing was grilled or promoted.

Plus, at every cold contact: the owed-answers statement was made in the KISS presentation, or the debt was zero and nothing was said.

No ingress unit is silently dropped, and no master session is born inside the scaffolded goal as one of its seats' occupants.
</done-contract>
