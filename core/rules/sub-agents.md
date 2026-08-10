# Sub-Agents

**MANDATORY. NO EXCEPTIONS.** Every dispatch of a worker — Agent-tool sub-agent, CLI worker, or API worker — MUST pass the Pre-Dispatch Gate below before it is sent. Skipping the gate is a rule violation, even for "quick" or "simple" dispatches. Dispatched workers do not reliably invoke skills on their own; the dispatcher carries that responsibility.

## Pre-Dispatch Gate

| # | Step | Requirement |
|---|------|-------------|
| 1 | Match | Scan the installed skill list and identify EVERY skill the planned task triggers — any source (RBTV, sb-os, user-defined, plugin), matched on each skill's description, never on a hardcoded keyword table. |
| 2 | Name + path | For each match, the dispatch prompt MUST contain an imperative directive — "Invoke `<skill-name>` and follow it exactly" — AND the skill file's workspace-root-absolute path so the worker can read it. Imperative only ("invoke", "follow exactly", "execute"); never permissive ("may", "consider", "can"). Mere mention of the skill name is insufficient. |
| 3 | Write hygiene | A dispatch that will CREATE, WRITE, or MOVE files gives every target path workspace-root-absolute — never bare-relative (a worker resolves relative paths from its OWN working directory, which is not guaranteed to match the dispatcher's). On return, VERIFY each claimed file exists at its intended path before trusting the report. |
| 4 | Environment hygiene | An in-process worker INHERITS the dispatcher's environment — including `TMUX`/`TMUX_PANE` — so it is born holding the dispatcher's OWN pane as its default target, and any tool acting on "the current pane" hits that pane WITHOUT NAMING IT. Every dispatch MUST bind the worker to a hermetic environment as a PRECONDITION in the prompt, before the worker's first command: unset `TMUX`/`TMUX_PANE`, and grant no terminal-multiplexer commands and no coordination-bus writes. A worker that genuinely needs the live environment MUST name its target explicitly, never inherit one. **This step is UNCONDITIONAL** — a bar keyed on ANTICIPATED contact never fires, because the target arrives from the environment rather than the prompt. |

You MUST NOT dispatch until the prompt satisfies all four steps. If you catch yourself about to dispatch without the gate, STOP and rewrite the prompt.

## Red Flags — STOP and Rewrite

| Thought | Action |
|---------|--------|
| "The worker will auto-discover the skill" | STOP. Claude sub-agents see skill descriptions but unreliably invoke them; CLI and API workers see nothing. Name each skill, with its path. |
| "This dispatch is too small to need the gate" | STOP. Size does not waive the gate. |
| "I already named the skill last dispatch" | STOP. Each dispatch is independent. Name it again. |
| "This task has nothing to do with the terminal — the environment bar is overkill here" | STOP. The worker holds your pane whether or not the task mentions one, and routine commands act on the CALLING pane. Bind it hermetic. |
| "I'll tell the worker to be careful with the live environment" | STOP. Care is not a bound. Unset the variables in the prompt as a precondition, before its first command. |

## Scope

Applies to EVERY worker dispatch — Agent tool calls (including parallel and background dispatches), CLI worker spawns, and API worker dispatches. It does NOT apply to the `Skill` tool (direct skill invocation by the parent agent). Model selection, floors, and haiku eligibility are NOT this rule's concern — orchestration routing (`{rbtv_path}/orchestration/skills/orchestrating/cards/routing.md` §7 — resolve `{rbtv_path}` from `rbtv.json`) owns model policy.
