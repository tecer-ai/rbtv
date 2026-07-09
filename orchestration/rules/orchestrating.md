# Orchestrating

**MANDATORY. NO EXCEPTIONS.** When work in front of you matches an Intake Trigger below — or a Mid-Task Escalation fires while you are already working — you MUST invoke the `rbtv-orchestrating` skill and let it run the work, instead of dispatching workers ad hoc yourself. The user does NOT have to name orchestration; this rule pulls orchestration-shaped work into the skill on your own detection.

This is the discoverability layer for `rbtv-orchestrating`. The skill owns HOW to orchestrate; this rule owns WHEN you must reach for it.

## Decide up front — plain task only

When a plain task (not a plan execution, not a dispatched task) arrives, decide BEFORE any other action whether to hand the work out or do it yourself.

| Hand it out (orchestrate) when | Do it yourself when |
|--------------------------------|---------------------|
| It splits into independent pieces | It is small / quick — dispatch overhead exceeds doing it |
| A piece suits a cheaper or specialized worker better | It leans heavily on THIS conversation's history and the user's preferences |
| It is long enough that doing it all solo would fill context before the end | It is tightly coupled or exploratory — no self-contained task can be written yet |
| You can describe the piece completely in a self-contained task artifact | It needs live back-and-forth with the user while it runs |

Lean toward distributing when the work fits — orchestration is under-used, not over-used.

**Plain-task-vs-plan gate:** this up-front decision does NOT re-fire when executing a plan or a dispatched task — the plan's `orchestrated:` flag (Intake Trigger #2) already carries that decision.

## Intake Triggers — fires on ANY

Scan the task at the moment it arrives. If ANY single row matches, the Action below is mandatory — one match is enough.

| # | Trigger | Matches when |
|---|---------|--------------|
| 1 | Explicit ask | The user says "orchestrate this", "run this end-to-end with workers", "use kimi/codex/claude-cli/opencode for X", or names the skill directly |
| 2 | Plan with orchestration flag | An `rbtv-planning` plan is in hand and declares it will be orchestrated (orchestration-aware DEEP/LIGHT) |
| 3 | ≥3 coordinated dispatches forecast | The work, as scoped, will need three or more sub-agent dispatches that share state or build toward one goal |
| 4 | Multi-hour AFK intent | The user wants the work run unattended / overnight / "while I'm away" — a long-horizon run, not a single turn |
| 5 | ≥2 worker types needed | The work needs two or more distinct worker kinds (e.g., a CLI code executor AND a reviewer, or research AND build) |
| 6 | Fitting single dispatch | A single self-contained unit of work (one bounded coding task, one research brief, one synthesis) fits an installed + available worker that beats the conductor on cost or fit. Fires at MINIMAL ceremony — a task artifact + spine, no full intake round (the skill's intake §1 owns the ceremony level). Does NOT fire for a true quick lookup (a single fact, a path, one file read) — that answers directly, no dispatch. |

## Mid-Task Escalation — fires while already working

Re-check continuously during execution. Crossing ANY threshold below means STOP improvising and invoke `rbtv-orchestrating` now, handing it the work already in flight.

| # | Escalation trigger | Crossed when |
|---|--------------------|--------------|
| 1 | Context filling while work remains | The up-front decision (above) is the PRIMARY switch — if you chose to work solo, revisit that decision first. This escalation fires when the harness has surfaced a compaction / auto-compact warning while more than one further dispatch of work remains. |
| 2 | About to dispatch the 3rd sub-agent for the same goal | You are reaching for a third sub-agent in service of one goal — ad-hoc dispatch has become orchestration |
| 3 | Cross-repo coordination emerges | The work has grown to span more than one repository and the pieces must be coordinated |

## Counter-List — NEVER fires

These bound FULL orchestration (multi-phase, multi-worker, AFK). Resolve precedence in order — read it, do not re-arbitrate it each task:

1. A fired Intake Trigger or Mid-Task Escalation WINS — a counter-list item NEVER overrides it.
2. No trigger fired AND the work is ONLY a row below → FULL orchestration does not fire (firing it would be over-firing).
3. A fitting single dispatch (trigger #6) is NOT full orchestration — minimal ceremony; this list does not block it.
4. A true quick lookup (no worker, no dispatch) stays fully out.

| The rule does NOT fire for | Because |
|----------------------------|---------|
| A single dispatch needing no worker | A task the conductor answers directly with no model dispatch — a quick lookup, a fact, a file read. (A single dispatch that DOES route to a fitting worker is trigger #6, minimal ceremony — not a counter-list exclusion. The bar that separates them is intake §1: a worker dispatch needs a task artifact + spine; a direct answer needs neither.) |
| Quick lookups | A fact, a path, a file read — answerable directly |
| Tasks under ≈30 minutes | Too small to amortize an intake + state spine |
| Work owned by a specialized workflow | `source-mining`, wiki ingest, and planning itself already own their flow — let that workflow run; do NOT wrap it in orchestration |

## Action on Fire

When a trigger fires, your visible response MUST be: `Invoking rbtv-orchestrating — [the trigger that fired].` Then call the `Skill` tool with `rbtv-orchestrating` and follow its core protocol exactly. Do NOT begin dispatching workers, authoring task artifacts, or routing by hand first — the skill's intake owns all of that. (The `rbtv-orchestrating` loader is installed at the workspace by `install.py`; if the loader is absent, the workspace did not install the orchestration module — surface that rather than improvising orchestration.)

## Red Flags — STOP and Invoke

If you catch ANY of these thoughts, you are rationalizing past a fired trigger. Delete the thought and invoke `rbtv-orchestrating`.

| Thought | Action |
|---------|--------|
| "I'll just dispatch these few agents myself — faster than loading the skill" | STOP. ≥3 coordinated dispatches IS the trigger. Invoke the skill. |
| "This started small; I'll keep going and reach for the skill if it grows" | STOP. The escalation thresholds exist for exactly this drift. Invoke it now. |
| "No state spine needed for this one" | STOP. If a trigger fired, the skill decides ceremony — not you. Invoke it. |
| "The user didn't say 'orchestrate', so the rule doesn't apply" | STOP. Triggers 3–5 fire on the work's shape, not the user's wording. |
| "It's basically a source-mining job, close enough to wrap in orchestration" | STOP. Counter-list: a specialized workflow owns it. Run that workflow, do NOT orchestrate it. |

## Scope

This rule governs WHEN to reach for `rbtv-orchestrating`. It does not govern how the skill orchestrates (the skill's core protocol and cards own that), nor does it fire when the only matching condition is a counter-list item. It does not apply once `rbtv-orchestrating` is already running — its intake card owns every decision from that point. Obey any injected context-refresh advisory at the next safe checkpoint.
