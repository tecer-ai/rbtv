# Card: Intake

The run-opening card for `rbtv-orchestrating`. Open it once, at the start of a run, before any dispatch. It takes a run from "user has a goal or a plan" to "a dispatchable work surface exists on disk and the run's mode is set." When this card's steps are complete, routing begins.

Iron rule it serves (from the core protocol): **no dispatch without a self-contained task artifact + a state spine on disk.** Intake is where those artifacts come to exist. The selector, the budget question, the run-mode question, and the sdd question are all answered HERE, in one pre-AFK exchange, so the rest of the run can proceed without interrupting the user.

---

## Sequence

Run these in order. Steps 1–2 establish the work surface; steps 3–7 are the single pre-AFK exchange (one question round); step 8 finalizes.

1. Pre-flight checks
2. Choose the entry door (scored)
3. Initialize the state spine
4. Ask the budget question
5. Ask the code-backend question (code work only)
6. Run the question round
7. Select the run mode
8. Confirm and hand off to routing

---

## 1. Pre-flight checks

Before anything else, confirm the run is viable and capture what the doors need:

| Check | Action |
|-------|--------|
| Work is multi-step | A quick lookup or a trivial <~30-min task is below the orchestration bar — say so and stop. The module rule's counter-list (`{rbtv_path}/orchestration/rules/orchestrating.md`) governs this; do not orchestrate work it excludes. EXCEPTION — a single named-model CLI dispatch (the SKILL's advertised "use kimi for X" front door) IS in scope at minimal ceremony: it still needs a task artifact + spine, but skips the door selector and the full question round. This is distinct from a "quick lookup" (no artifact, no model dispatch), which stays out. |
| Workspace identified | Resolve the target workspace (where the work and its artifacts live). Read its root `CLAUDE.md` for placement conventions. |
| Inputs located | Plan door: locate the plan + its companion artifacts. Goal door: capture the goal prompt and any files/data it points at. |
| Guidance-file presence noted | If code work will route to a CLI worker, note whether the workspace carries that worker's guidance file (`AGENTS.md`, agent file, etc.). A missing one is surfaced at routing, not invented here. |

**In-run light path — a trivial task inside a running orchestration (the triviality bar).**

A run already in flight may hit a task so trivial that full per-task ceremony (a dispatch prompt, a separate task artifact, a worker round-trip) is pure overhead — the D10 folder-rename pathology (~95% ceremony on a one-second op). For such a task ONLY, the conductor MAY self-execute at light ceremony, overriding the plan's `executor:` pin for THAT task alone. This is the sole sanctioned carve of core Invariant 1 — read core-protocol.md Invariant 1 for the carve's authority; this card owns the bar and the gesture.

**The triviality bar — ALL six conditions MUST hold (else route to a worker normally; fail-safe is to dispatch, never to self-execute on doubt):**

| # | Condition |
|---|-----------|
| 1 | Single deterministic file-op against an EXPLICIT source→target mapping (a move/rename/stamp/flip — never "figure out where X goes"). |
| 2 | No content authoring (no new prose, code, rule text, or design content — authoring the deliverable stays barred by Invariant 1). |
| 3 | No rule / card / contract / architectural-constraint semantics — purely mechanical bookkeeping or file placement. |
| 4 | Validation is exactly ONE deterministic command (a clean `git status`, one `pytest` line, a single grep). |
| 5 | Reversible (trivial undo) and touches NO user content destructively. |
| 6 | The profile's `stakes_tier` is RESOLVED and low. The bar NEVER clears while stakes are `unresolved`. |

**The self-execute gesture + record.** When all six hold: surface the task and the cleared bar to the owner as a multiple-choice ask ("self-execute this ≈2-min reversible op, or dispatch it?"); on approval — or, in `autonomous` mode, as a LABELED confidence-rated unilateral decision — record it as a run-log event via the stamp script (`{rbtv_path}/orchestration/skills/orchestrating/scripts/stamp.py`), then self-execute. The override applies to the ONE bar-clearing task and expires; the next task keeps its pin.

**Light-path spine writes (one stamp call):** KEEP the run-log event (carrying the approval/decision), the deliverables row, and the plan checkbox; flip the task `status` only if a separate task artifact exists. DROP the dispatch prompt file (no worker is dispatched) and the separate task artifact when the plan task line is self-contained (Invariant 2's "no dispatch without an artifact" floor does not apply — there is no dispatch). All KEEP writes collapse into one `stamp.py` call; the conductor owns all of them (no worker, so the worker-stampable/conductor-only split resolves to conductor-only). When the self-contained task has NO task artifact, that one call carries `--no-task-file` so it skips the absent frontmatter surface and stamps the rest — never hand-edit the surfaces or trip the stamp-failure fallback (state.md §7 owns the flag). A bar-clearing op with NO plan presence (no checkbox, no deliverables row — e.g. an ad-hoc owner-named op inside a conductor-executed task) has NO stampable surface — `stamp.py`'s all-or-nothing target validation cannot bind; record its run-log event as a MANUAL append with the deviation disclosed (2026-06-10 pilot).

**Boundary — distinct from the entry-level single dispatch.** The minimal-ceremony single dispatch in the EXCEPTION row above is about ENTRY (a fitting unit routes to a worker at run open). This in-run light path is about a trivial task INSIDE a running run that the conductor self-executes. Both are minimal-ceremony; only the in-run light path carves Invariant 1, and only under the six-condition bar.

There is NO code-vs-non-code hard redirect at intake. Code work is routed, not rejected — the code-backend question (step 5) handles it. (Supersedes the retired plan-orchestration pre-flight redirect, per D20.)

---

## 2. Choose the entry door (scored)

Two ORTHOGONAL decisions, taken in this order — do not conflate them:

1. **Artifact presence decides the DOOR first.** A `rbtv-planning` plan already on disk → **Plan ingest**, full stop (the rubric below does NOT override an existing plan — a plan that scores "Complex" is still ingested, not re-planned). No plan → **Goal-prompt intake**, and only THEN does the prep-level selector apply.
2. **The prep-level selector applies ONLY to the goal-prompt branch** — it sets how much ceremony the authoring takes, not which door.

| Door | When | What happens |
|------|------|--------------|
| **Plan ingest** | `rbtv-planning` artifacts already exist (plan + `shape.md`/`decisions.md` + task files) | Ingest them directly: read the full plan and its companion, map phases to tasks. The artifacts ARE the work surface — no authoring needed; the selector is skipped. |
| **Goal-prompt intake** | No plan exists — only a goal prompt | Score the prep level (below), then author the spec + task files from the goal following the shared authoring core. The authored artifacts become the work surface. |

**Prep-level selector (D2a) — goal-prompt branch only.** Score the body of work with the shared complexity rubric at `{rbtv_path}/orchestration/workflows/_shared/authoring/complexity-rubric.md`. Read the rubric; do not reproduce its axes or bands here. The band it returns sets the prep level:

| Band | Prep level | Behavior |
|------|------------|----------|
| Simple | Conductor-led prep, IN-SESSION | The conductor authors the task/spec artifacts itself, in-session (no writer-agent dispatch) — lightest prep — then proceeds. Authoring the dispatchable ARTIFACT is intake scaffolding, NOT the deliverable: core Invariant 1 bars writing the user's output, not preparing the dispatchable surface. |
| Moderate | ASK the user which prep | Surface the score and ask whether to do conductor-led prep (in-session) or escalate to interactive planning. |
| Complex / decision-dense | Interactive `rbtv-planning` with the user | Hand off to `rbtv-planning` to resolve the plan WITH the user before any execution. |

All bands are user-overrideable: state the score and the prep level it selected, and accept an explicit override without re-scoring.

**Goal-door authoring — in-session vs dispatched.** Simple band → the conductor authors in-session itself (no writer-agent dispatch). Moderate-prep (when the user chooses conductor-led prep) → the conductor MAY dispatch writer agents to author the artifacts; a writer-agent dispatch goes through the normal routing → dispatch-wrapper path like any other dispatch (it is not a special intake mechanism). Whether authored in-session or dispatched, the writer follows the shared authoring core — task-file contract, spec template for code work, dependency ordering, and `decisions.md` discipline — at `{rbtv_path}/orchestration/workflows/_shared/authoring/`. They read that core; this card does not restate its contracts. Order the authored task set by the core's dependency-ordering rules and run its validity checks before the set is considered dispatchable.

---

## 3. Initialize the state spine

Every run gets the three-file spine before dispatch (D12). The State card owns the file semantics, the registrar discipline, and the propagation rules — open it for those; this card only fixes WHERE the spine is created and HOW it is initialized.

| File | Initialized as |
|------|----------------|
| `run-log.md` | New, empty append-only audit log. The run's first event rows land here. |
| `state-capsule.md` | New, with the resume point set to "intake complete," an empty delegation map (filled at routing), and empty active-red-sets / active-doubts sections. |
| `decisions.md` | Plan-backed run: REUSE the plan's worker-facing decisions file (do not create a second one) — `decisions.md` for a plan authored after the D13 rename, or `shape.md` for a plan authored before it (the rename lands at p4-2; plans built earlier, including this build's own, carry `shape.md`). Match the filename the plan actually carries. Plan-less run: create a new empty `decisions.md` here at intake. |

**Where the spine lives.**

| Run kind | Location | Commit |
|----------|----------|--------|
| Plan-backed | Alongside the plan, in the plan folder | Per the plan's own conventions |
| Plan-less | **Workspace-local, alongside the work** — folder naming follows the target workspace's conventions (e.g., a `docs/` subfolder, as the validated pilots used) | **Committed to that workspace's repo** |

Plan-less edge case — workspace has NO git repo: the spine + intake artifacts still land workspace-local on disk, and the run-log records a no-commit condition (the spine cannot be committed because the workspace is not a repo). Do NOT halt the user for this and do NOT relocate the artifacts elsewhere — resolve it silently per this rule. (Resolved 2026-06-07; no mid-run user ask.)

---

## 4. Ask the budget question

Fires at EVERY run, no exception (D6). Ask whether any model should be swapped to save spend on this run, presenting the provisional tier map before the user goes AFK.

NEVER estimate spend in currency. Reliable per-run dollar cost cannot be computed and attempting it wastes context — the choice is framed as worker TIERS (cheaper vs. more capable model per work-cluster), never as a projected dollar amount.

| Element | Content |
|---------|---------|
| The ask | "Any model to swap to save this run, or run at the default tiers?" |
| Sketch the provisional map | Routing has not run yet, so the map is PROVISIONAL, but it STILL names a concrete `(model, variant)` pair per work-cluster — NEVER a bare provider. Assign each phase/work-cluster its DEFAULT pair by calling the routing §2a selector script (`route.py` per `{rbtv_path}/orchestration/skills/orchestrating/cards/routing.md` §2a — one profile per cluster, carrying its boundedness band) against the installed manifests: bounded code → the cheapest capable code-executor variant (e.g. `kimi:default`), judgment-dense work → a top-tier Claude variant (`claude:opus`), review → the pinned reviewer-floor variant (`claude:opus`), text synthesis → the cheapest capable text variant (e.g. `deepseek:v4-flash`). The `(model, variant)` pairs shown here are ILLUSTRATIVE — the binding pair for each cluster is whatever the live §2a run returns against the installed manifests, never a hardcoded pair. The user approves a ceiling / swap POLICY against this sketch, not a finalized assignment; routing re-surfaces the binding map at step 8. |
| Spend forecast — per-variant `cost_class` | Each work-cluster's line shows its assigned `(model, variant)` pair and that variant's `cost_class` read from its manifest (`models/manifest-schema.md` §2 — `cheapest` · `low` · `mid` · `high` · `premium`), NOT a dollar figure. The user swaps on the relative cost class, not on an invented number. Flag any `(model, variant)` whose manifest carries `evidence_status: probe-pending` (the API chat/agentic variants) as **ESTIMATE-ONLY** — its `cost_class` is authored from the routing-matrix reference, not pilot-validated spend. |
| Name pairs, never bare providers | The budget summary NAMES `(model, variant)` pairs on EVERY row — e.g. `claude:sonnet`, `deepseek:v4-flash`, `kimi:default` — and NEVER a bare provider like "a top-tier Claude" or "DeepSeek". A bare-provider row is the "Claude as one entity" collapse this enumeration exists to kill (routing §2a "never collapses"; the run-log and this summary name the same pair). |
| Timing | The map is provisional at intake (routing finalizes assignments) — present it as the cost-class policy the user is approving, and re-surface the final pair-named map at step 8. |

`cost_class` is a TIER LABEL (`cheapest` / `low` / `mid` / `high` / `premium`, cost-ascending — `premium` ranks above `high`, reserved for premium-priced top-tier models e.g. Fable 5; cost-ascending selection never auto-picks it — pinned-roles reachability), NEVER a dollar amount — this section's opening no-currency rule and core invariant 6 both hold: the forecast stays in cost-class tiers, never currency.

The budget answer feeds routing's BUDGET filter; a model swap the user approves here is the standing delegation map for the run.

---

## 5. Ask the code-backend question (code work only)

For code work, ask ONCE per run which backend executes it (D20). Skip this step entirely for non-code runs.

| Backend | What it is |
|---------|------------|
| **CLI fleet** | External-CLI workers execute (e.g., Kimi executes, Claude reviews) — cheap, validated. The default code path. |
| **sdd** | `superpowers:subagent-driven-development` — Claude-heavy, TDD-strict, in-session. Treated as ONE composite dispatch wrapped by the same outer gates (return verification, cold verifier at feature boundaries). |

If `superpowers:subagent-driven-development` is NOT installed, take the CLI/native path silently — do not ask, do not surface sdd as an option that cannot be honored.

---

## 6. Run the question round

ONE round of clarifying questions before the user goes AFK — the validated pilot pattern (the hypresent pilots ran a single up-front round, then the user went AFK while the run proceeded). Fold the budget and code-backend asks above into THIS round so the user answers everything once.

| Rule | Detail |
|------|--------|
| Research before asking | Resolve what can be resolved without the user first — read files, check the workspace, dispatch a doc-reader or web-capable worker for open facts. Bring to the user ONLY what genuinely needs human executive decision. |
| Multiple choice with recommendations | Pose each question as options (a / b / c …) with a recommended option and its reasoning — never an open prompt. |
| One round | This is the only pre-AFK round. Batch every question into it. After it, the run proceeds without interrupting the user except at genuine halts (the halt taxonomy governs those, not new question rounds). |
| Pace if dense | If the round carries many questions, lead with a one-line map of what is being asked, then group the questions — do not dump them all undifferentiated. |

---

## 7. Select the run mode

Capture how the run handles its own boundaries and decisions (D21). Record the choice in `state-capsule.md` (Run Configuration).

| Mode | Behavior |
|------|----------|
| **Halt** | Stop after each phase's reviewer and wait for go-ahead. Doubts halt. USER-EXECUTED-ONLY tasks halt for the user to perform them. |
| **End-to-end** | Run phases continuously without stopping at checkpoints. Doubts still halt. USER-EXECUTED-ONLY tasks still halt. |
| **Autonomous** | Run continuously and decide unilaterally on doubts and USER-EXECUTED-ONLY tasks too. Every unilateral decision is appended to `run-log.md` as a LABELED, confidence-rated row for post-hoc review. Plan-marked HARD halts (irreversibility gates) are NEVER overridden; user content is never destroyed. |

Halt-type behavior by mode:

| Halt type | halt | end-to-end | autonomous |
|-----------|------|------------|------------|
| Checkpoint between phases | HALT | skip | skip |
| Doubt escalation from a worker | HALT | HALT | skip + log decision |
| USER-EXECUTED-ONLY task | HALT | HALT | skip + log defaults accepted |
| Plan-marked HARD halt (irreversibility gate) | HALT | HALT | HALT (never overridden) |

**Context-refresh setting** (asked alongside the run mode):

| Setting | Behavior |
|---------|----------|
| **Suggest** (default) | At approved clean phase boundaries only, ask whether to stop and resume with a fresh conductor from `state-capsule.md`. Never refresh mid-phase or before the full delegation map is set. |
| **Off** | Keep the same conductor unless the session is interrupted. |

If the user confirms without naming a refresh setting, record `context_refresh: suggest`.

---

## 8. Confirm and hand off to routing

First, **re-write `state-capsule.md` (atomic overwrite) with the now-finalized run configuration** — the capsule was initialized at step 3 before the run mode (step 7), budget answer (step 4), and code backend (step 5) existed; this step writes them in (run mode, context-refresh setting, the approved delegation map). The State card owns the atomic-overwrite mechanics.

Then echo back the run's shape in one pass, then proceed:

- Door taken (plan ingest / goal-prompt intake) and the rubric score that selected it.
- Spine location (and, for a plan-less no-repo workspace, the flagged no-commit condition).
- The final delegation map (tier per work-cluster) the user approved (budget answer applied).
- Code backend (CLI fleet / sdd / non-code) if code work.
- Run mode + context-refresh setting.

Routing begins next. Do not open the routing card from here — the situation table in the core protocol points to it; follow the situation, not a hardcoded chain.
