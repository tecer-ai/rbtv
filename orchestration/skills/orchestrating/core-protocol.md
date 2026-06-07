# Core Protocol — rbtv-orchestrating

The always-loaded heart of `rbtv-orchestrating`. SKILL.md loads THIS file at the start of any orchestration and keeps it in context for the whole run. It carries three things and nothing else: the **invariants** every orchestration obeys, the **situation table** that routes the run to the right card just-in-time, and the **capability summary** of the model packages installed in this workspace. The cards hold the situational mechanics; this core holds only what is true in every situation.

Read it once, hold it all run. When a situation arises, the situation table names the ONE card (or model manual) to open for it — open that card, follow it, return here for the next situation. Never front-load the cards; never improvise a step the table maps to a card.

---

## Invariants — true in every situation

These are non-negotiable. Every card elaborates them in its own situation; none may contradict them. If a card's instruction ever appears to conflict with an invariant, the invariant wins and the conflict is surfaced to the user.

| # | Invariant | What it means in practice |
|---|-----------|---------------------------|
| 1 | **Never execute the work yourself** | The conductor routes, packages, gates, and reconciles — it does NOT write the DELIVERABLE (the user's code/content/output). Routing always produces a worker; "I'll just do this one myself" is the failure this skill exists to prevent. This bars writing the deliverable — NOT the orchestration scaffolding: initializing the state spine, and (simple-band intake) authoring the dispatchable task/spec ARTIFACTS, are intake prep, not the deliverable. The hands-on conductor actions are the explicitly-named ones: spine + intake-artifact authoring, recovery commits, reconciliation reads, exit probes. |
| 2 | **No dispatch without a self-contained task artifact + a state spine on disk** | Artifacts are mandatory; ceremony is optional. Before ANY worker is dispatched, a task file that satisfies the task-file contract AND the three-file state spine exist on disk. A goal in chat is not a dispatchable unit — intake makes it one first. |
| 3 | **Disk = truth; verify every return** | The worker's return message is a HINT, never the truth. EVERY return — `DONE` included, resumes especially — is reconciled against actual repo state (`git status` / `git log`) and the evidence files on disk before it is trusted or logged. Message and disk disagree → disk wins, logged. |
| 4 | **Halts are the loop, never a blind retry** | A `doubt_policy: halt` stop is the normal, productive path — the entry to Decide→Resume, not a failure to retry away. NEVER blind-re-dispatch a halted worker "to see if it resolves"; read the blocker, decide, resume. (Five-for-five correct halts with zero wasted retries is this design's strongest evidence.) |
| 5 | **Evidence must be plausible** | The return is named-field so integrity tripwires are MECHANICAL field checks, not eyeballing: a claimed commit hash must be in `git log`; an implausible `WALL_MS` means the check did not run; a silent skip means the gate did not pass. Plausibility is tested, never assumed. |
| 6 | **Ask the budget question at every intake** | EVERY run, no exception — AFK or fully interactive: ask whether any model should be swapped to save spend, and show the projected per-model spend. The forecast-before-AFK timing applies only when the user is going AFK; an interactive run still asks the question, it just need not front-load the forecast. The answer is the run's standing delegation map. |
| 7 | **Follow the ask-the-user taxonomy** | Interrupt the user ONLY at genuine executive decisions and the run mode's defined halts (checkpoints, doubts, USER-EXECUTED-ONLY steps, HARD irreversibility gates). Resolve everything resolvable WITHOUT the user first (re-read decisions → doc-reader → only then halt). One pre-AFK question round; no new question rounds mid-run. |
| 8 | **Adaptive brain floor — a weaker conductor escalates every judgment point** | Max-reasoning is the intended conductor. A weaker model orchestrating MAY still dispatch and track mechanical work, but EVERY judgment point — doubt rulings, recovery commits, ADX errata, allowlist grants, precondition overrides — becomes a halt-and-ask. A downgraded conductor never rules alone. |
| 9 | **Depth cap ≤ 2 conductor levels** | Agent-tool sub-agents CANNOT spawn sub-agents (the nesting wall). A second conductor level is achieved ONLY through CLI workers as separate OS processes (`kimi`, `codex exec`, `claude -p`). The top conductor plus at most one CLI-driven sub-conductor — never stack deeper. |

The invariants are the floor; the cards are how each one is honored in a specific situation. A run that violates any invariant is off-protocol regardless of what a card said.

---

## Situation table — open the named card when the situation arises

This is the core's router. Each row maps a situation in the run to the ONE card that owns it. When the situation arises, open that card (JIT), follow it, and return here. Do NOT open cards ahead of their situation, and do NOT hardcode a card-to-card chain — every transition comes back through this table.

| Situation | Card to open | Path |
|-----------|--------------|------|
| **Run is opening** — a user has a goal or a plan; no dispatchable surface exists yet | **Intake** — choose the door (scored), init the spine, ask the budget + code-backend + run-mode questions in one pre-AFK round | `cards/intake.md` |
| **A task is ready to dispatch** — the work surface exists; which worker gets this task? | **Routing** — boundedness → stakes → budget tree, pinned-role floors, topology, strategy leaf, batching | `cards/routing.md` |
| **A worker has been chosen** — package the task into an actual dispatch | **Dispatch-wrapper** — header+payload packaging, binding addendum, the unified five-field return schema, reference-doc inlining | `cards/dispatch-wrapper.md` |
| **A return has arrived** (any status, `DONE` included) | **Verification** — run the return gate: tripwire field checks → repo-state reconciliation; then review gates and the cold verifier for development work | `cards/verification.md` |
| **A quality boundary is reached** — a feature/phase commit boundary, or the run is about to be declared done | **Verification** — fire the review gate, the cold verifier at feature boundaries, and the conductor-executed exit probes before done | `cards/verification.md` |
| **The run is being closed** — exit probes held; the run is certifiable as done | **Verification** — run finalization (§6): complete the exit scorecard, set the honest status (COMPLETE / COMPLETE PENDING USER ACTION), and surface every Human Review block + low-confidence/red-flag decision before reporting completion | `cards/verification.md` |
| **A worker did not cleanly finish** — it halted on a doubt, returned `BLOCKED`, died mid-run (exit-75 / hang / crash), or its return drifted from disk | **Halt-recovery** — Halt→Decide→Resume, the L1/L2/L3 recovery ladder, the doubt-escalation chain, red-set bookkeeping, precondition override, USER-EXECUTED-ONLY handover | `cards/halt-recovery.md` |
| **A state file must be written** — a dispatch goes out, a return comes back, a gate/probe fires, a decision affects queued work | **State** — the three-file spine semantics, registrar discipline, propagation, the dual-write rule | `cards/state.md` |
| **The run is resuming or refreshing** — a new session, or an approved clean phase-boundary refresh | **State** — rebuild from `state-capsule.md` first, then the `run-log.md` tail, then `decisions.md`; the capsule IS the resume contract (no separate handoff file) | `cards/state.md` |
| **A task will be dispatched to a CLI model** — a chosen worker is `kimi`, `codex`, `claude-cli`, `qwen`, … | **The model's rendered manual** — open it JIT at first dispatch to that model for the exact invocation shape (command, flags, work-dir, prompt transport, exit handling, resume). **Availability guard:** the manual exists only when that model package is installed AND the render step (P3) has produced it — if `models/{model}/` is absent, the CLI dispatch is not available; routing routes to an Agent-tool Claude tier instead or halts (routing card §1). | `models/{model}/manual.md` |

Reading the table: most situations map to a card; a CLI dispatch additionally maps to the chosen model's manual (the dispatch-wrapper card packages the GENERIC dispatch, the model manual supplies the model-specific invocation). **Parallel waves:** when several workers return concurrently, each return is processed INDEPENDENTLY through the same Verification gate (one return = one gate run); the per-wave reconciliation — committing at wave boundaries to restore git-diff resolution — is the State card's wave-commit discipline (routing §8 sized the wave). A situation not in this table is either an invariant question (answer it from the invariants above) or a sign the run has drifted off-protocol — stop and reconcile, do not invent a step.

---

## Capability summary — the model packages installed here

One line per installed model package, always in the core so routing can recall what is routable WITHOUT opening a manual (the full manual is read JIT at first dispatch). This is the recall surface the boundedness tree uses to know which workers exist; the routing card still confirms availability against the live `models/` folder (disk = truth) before assigning.

The availability line below is written by the installer (`install.py`) at install time — it names which packages are present in THIS workspace and which are absent (the installer replaces only the content BETWEEN the `ORCH:AVAILABILITY` markers; the markers are preserved so re-install is idempotent). Until an install runs in a workspace, the marker region carries its fallback text and the live `{rbtv_path}/orchestration/models/` folder is authoritative. Trust the live `models/` folder over this line on any mismatch, and log the mismatch (the routing card owns that check).

<!-- ORCH:AVAILABILITY:BEGIN -->
> **Model packages installed:** _(populated by install.py at install time — until an install runs, treat the live `{rbtv_path}/orchestration/models/` folder as authoritative)_
> **Absent:** _(populated by install.py)_
<!-- ORCH:AVAILABILITY:END -->

Per-model capability lines — a STATIC reference roster of the model packages this skill can carry, NOT a list of what is installed here. A line's presence in this table says nothing about routability: routability is decided ONLY by the installer-baked availability block above + the live `models/` folder. Routing reads the installed package's manifest for the full field set — these lines are the at-a-glance recall, not the routing inputs:

| Model package | One-line capability (recall only — manifest is authoritative) |
|---------------|----------------------------------------------------------------|
| **kimi** | Code-executing CLI worker — writes code, runs scripts/servers, commits locally; the validated bounded-code executor. Resume via session id. |
| **codex** | Code-executing CLI worker (`codex exec`) — separate-process execution; live-proven once. |
| **claude-cli** | `claude -p` headless worker — natively loads workspace `CLAUDE.md`/rules; usable as a CLI-driven sub-conductor (process boundary clears the nesting wall). |
| **qwen** | Web-capable CLI worker — the research-leaf executor; carries the sources-manifest pointer when one is provided. |

A line here is recall, not permission: routing routes only on `(model, variant)` pairs read from an INSTALLED package's manifest, and the capability lines for absent packages are simply not in play this run. The installer-baked availability block above is the single source for what "installed" means in this workspace.

---

The run opens at the situation table's first row (Intake) and thereafter returns to the table after every situation. Cards are opened JIT — never front-loaded — and the run is declared done ONLY when Verification's exit gates certify it (and then closed through Verification's finalization), never on a return message alone. Everything situational lives one open-the-card away; this core is only what must be true everywhere and recalled instantly.
