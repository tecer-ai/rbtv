# Native-Lane Sub-Agents

**MANDATORY. NO EXCEPTIONS.** Whenever you dispatch a sub-agent through the harness's OWN native
sub-agent tool (Claude Code's Agent tool, or the equivalent in another harness) — the NATIVE lane
of the standing sub-agent lane — you MUST obey the four bounds below. They are judgment-honored,
not machine-enforced: nothing in the native tool refuses a breach, so compliance is yours alone.

This rule is the NATIVE-lane half of the sub-agent cage only. It does NOT state, restate, or
enforce the CLI-lane dispatch capability's checks (catalog-bound, profile-bound, environment
allowlist, and the rest) — those are machine-enforced, fail-closed, inside that capability's own
code, and are that capability's rule to carry, never this one's.

## The cage — four bounds, every native-lane dispatch, no exceptions

| Bound | Rule |
|-------|------|
| Native-first | Use the harness's native sub-agent tool BY DEFAULT whenever it is available. Reach for the CLI dispatch capability ONLY when the task needs a different model family or harness than the one you are running in, or needs a capability the native tool cannot provide. Never reach for the CLI lane out of habit or convenience when the native tool would do — this is how you decide native vs CLI. |
| No bus access | A native sub-agent MUST NEVER write to the coordination bus, message the owner, or create goals, seats, or jobs. Its results return ONLY to the dispatcher that spawned it. |
| Dispatcher-owned lifecycle | A native sub-agent MUST die with the dispatching step or terminal. The dispatcher MUST collect its results before ending its own turn — never leave one running past that point. |
| No seat impersonation | A native sub-agent MAY reuse a cataloged seat's DEFINITION (its briefing content, its persona) but its output MUST NEVER be attributed to a taskforce seat. It is not, and cannot become, a seat. |

## Red Flags — STOP and reconsider

| Thought | Action |
|---------|--------|
| "This native sub-agent should post its own status to the bus / message the owner directly" | STOP. No bus access. Route the result back to yourself and post it yourself if it needs posting. |
| "I'll let this native sub-agent keep running after my turn ends, I'll check its output later" | STOP. Dispatcher-owned lifecycle. Collect the result before you end your turn, or the sub-agent must die with it. |
| "I'll have this sub-agent report as if it were seat X" | STOP. No seat impersonation. It may reuse seat X's definition; its output is never seat X's output. |
| "I'll reach for the CLI dispatch capability because it's what I know" | STOP. Native-first. Use the native tool unless the task genuinely needs another model family/harness or a capability the native tool lacks. |

## Scope

Governs the NATIVE instrument of the standing sub-agent lane only — any dispatch through a
harness's own built-in sub-agent tool. It does not govern the CLI-lane dispatch capability (a
separate, machine-enforced cage), and it does not govern dispatch to a taskforce seat over the
bus (governed session coordination, not this lane).
