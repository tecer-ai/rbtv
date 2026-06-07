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
| Work is multi-step | A single dispatch, a quick lookup, or a <~30-min task is below the orchestration bar — say so and stop. The module rule's counter-list governs this; do not orchestrate work it excludes. |
| Workspace identified | Resolve the target workspace (where the work and its artifacts live). Read its root `CLAUDE.md` for placement conventions. |
| Inputs located | Plan door: locate the plan + its companion artifacts. Goal door: capture the goal prompt and any files/data it points at. |
| Guidance-file presence noted | If code work will route to a CLI worker, note whether the workspace carries that worker's guidance file (`AGENTS.md`, agent file, etc.). A missing one is surfaced at routing, not invented here. |

There is NO code-vs-non-code hard redirect at intake. Code work is routed, not rejected — the code-backend question (step 5) handles it. (Supersedes the retired plan-orchestration pre-flight redirect, per D20.)

---

## 2. Choose the entry door (scored)

Two doors lead to the same dispatch protocol; the difference is only how the dispatchable artifacts come to exist (D2).

| Door | When | What happens |
|------|------|--------------|
| **Plan ingest** | `rbtv-planning` artifacts already exist (plan + `shape.md`/`decisions.md` + task files) | Ingest them directly: read the full plan and its companion, map phases to tasks. The artifacts ARE the work surface — no authoring needed. |
| **Goal-prompt intake** | No plan exists — only a goal prompt | Dispatch writer agents to author the spec + task files from the goal, following the shared authoring core. The authored artifacts become the work surface. |

**Selector (D2a).** Score the body of work with the shared complexity rubric at `{rbtv_path}/orchestration/workflows/_shared/authoring/complexity-rubric.md`. Read the rubric; do not reproduce its axes or bands here. The band it returns selects the door:

| Band | Door | Behavior |
|------|------|----------|
| Simple | Conductor-led prep | Author the artifacts yourself (lightest prep); proceed. |
| Moderate | ASK the user which door | Surface the score and ask whether to do conductor-led prep or escalate to interactive planning. |
| Complex / decision-dense | Interactive `rbtv-planning` with the user | Hand off to `rbtv-planning` to resolve the plan WITH the user before any execution. |

All bands are user-overrideable: state the score and the door it selected, and accept an explicit override without re-scoring.

**Goal-door authoring.** When authoring (conductor-led prep, or the moderate door's prep choice), the writer agents follow the shared authoring core — task-file contract, spec template for code work, dependency ordering, and `decisions.md` discipline — at `{rbtv_path}/orchestration/workflows/_shared/authoring/`. They read that core; this card does not restate its contracts. Order the authored task set by the core's dependency-ordering rules and run its validity checks before the set is considered dispatchable.

---

## 3. Initialize the state spine

Every run gets the three-file spine before dispatch (D12). The State card owns the file semantics, the registrar discipline, and the propagation rules — open it for those; this card only fixes WHERE the spine is created and HOW it is initialized.

| File | Initialized as |
|------|----------------|
| `run-log.md` | New, empty append-only audit log. The run's first event rows land here. |
| `state-capsule.md` | New, with the resume point set to "intake complete," an empty delegation map (filled at routing), and empty active-red-sets / active-doubts sections. |
| `decisions.md` | Plan-backed run: REUSE the plan's `decisions.md` (do not create a second one). Plan-less run: create a new empty `decisions.md` here at intake. |

**Where the spine lives.**

| Run kind | Location | Commit |
|----------|----------|--------|
| Plan-backed | Alongside the plan, in the plan folder | Per the plan's own conventions |
| Plan-less | **Workspace-local, alongside the work** — folder naming follows the target workspace's conventions (e.g., a `docs/` subfolder, as the validated pilots used) | **Committed to that workspace's repo** |

Plan-less edge case — workspace has NO git repo: the spine + intake artifacts still land workspace-local on disk, and the run-log records a no-commit condition (the spine cannot be committed because the workspace is not a repo). Do NOT halt the user for this and do NOT relocate the artifacts elsewhere — resolve it silently per this rule. (Resolved 2026-06-07; no mid-run user ask.)

---

## 4. Ask the budget question

Fires at EVERY run, no exception (D6). Ask whether any model should be swapped to save spend on this run, and show the projected spend before the user goes AFK.

| Element | Content |
|---------|---------|
| The ask | "Any model to swap to save this run, or run at the default tiers?" |
| Spend forecast | A delegation map showing projected spend PER MODEL for the planned work. Forecast basis: per-role token costs from `1-projects/rbtv-evolution/orchestration/learnings/learnings-kimi-worker.md` (worker dispatch sizes, run durations) and the costs in the companion `learnings-claude-subagents.md`. |
| Timing | The map is provisional at intake (routing finalizes assignments) — present it as the spend the user is approving, and re-surface the final map at step 8. |

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

Echo back the run's shape in one pass, then proceed:

- Door taken (plan ingest / goal-prompt intake) and the rubric score that selected it.
- Spine location (and, for a plan-less no-repo workspace, the flagged no-commit condition).
- The final delegation map + projected spend the user approved (budget answer applied).
- Code backend (CLI fleet / sdd / non-code) if code work.
- Run mode + context-refresh setting.

Routing begins next. Do not open the routing card from here — the situation table in the core protocol points to it; follow the situation, not a hardcoded chain.
