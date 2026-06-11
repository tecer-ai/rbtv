# Sub-Agents

**MANDATORY. NO EXCEPTIONS.** Every dispatch of a worker — Agent-tool sub-agent, CLI worker, or API worker — MUST pass the Pre-Dispatch Gate below before it is sent. Skipping the gate is a rule violation, even for "quick" or "simple" dispatches. Dispatched workers do not reliably invoke skills on their own; the dispatcher carries that responsibility.

## Pre-Dispatch Gate

| # | Step | Requirement |
|---|------|-------------|
| 1 | Match | Scan the installed skill list and identify EVERY skill the planned task triggers — any source (RBTV, sb-os, user-defined, plugin), matched on each skill's description, never on a hardcoded keyword table. |
| 2 | Name + path | For each match, the dispatch prompt MUST contain an imperative directive — "Invoke `<skill-name>` and follow it exactly" — AND the skill file's workspace-root-absolute path so the worker can read it. Imperative only ("invoke", "follow exactly", "execute"); never permissive ("may", "consider", "can"). Mere mention of the skill name is insufficient. |
| 3 | Write hygiene | A dispatch that will CREATE, WRITE, or MOVE files gives every target path workspace-root-absolute — never bare-relative (a worker resolves relative paths from its OWN working directory, which is not guaranteed to match the dispatcher's). On return, VERIFY each claimed file exists at its intended path before trusting the report. |

You MUST NOT dispatch until the prompt satisfies all three steps. If you catch yourself about to dispatch without the gate, STOP and rewrite the prompt.

## Red Flags — STOP and Rewrite

| Thought | Action |
|---------|--------|
| "The worker will auto-discover the skill" | STOP. Claude sub-agents see skill descriptions but unreliably invoke them; CLI and API workers see nothing. Name each skill, with its path. |
| "This dispatch is too small to need the gate" | STOP. Size does not waive the gate. |
| "I already named the skill last dispatch" | STOP. Each dispatch is independent. Name it again. |
| "No skill matches this task" | STOP. Re-scan the skill descriptions for partial matches before declaring none. |
| "The worker shares my working directory — a bare relative write path is fine" | STOP. Workspace-root-absolute write paths; verify each file landed on return. |

## Scope

Applies to EVERY worker dispatch — Agent tool calls (including parallel and background dispatches), CLI worker spawns, and API worker dispatches. It does NOT apply to the `Skill` tool (direct skill invocation by the parent agent). Model selection, floors, and haiku eligibility are NOT this rule's concern — orchestration routing (`orchestration/skills/orchestrating/cards/routing.md` §7) owns model policy.
