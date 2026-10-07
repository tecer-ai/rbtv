# Hook

A hook is a record of a shell command that a harness runs on a named event. Use it when the action must run independently of whether the agent follows prose instructions. An rbtv hook is not a prompt, an HTTP call or an exposure method.

Write `hooks/<name>.json` in the chosen component and follow [hook.schema.json](../templates/hook.schema.json). rbtv emits hook settings for Claude Code and Codex. It does not emit an OpenCode plugin. If OpenCode must enforce the action too, report that rbtv hooks cannot meet that requirement and stop the dependent implementation until a supported mechanism is agreed. A prose rule does not provide equivalent enforcement.

## Choose the event and cases

Name the event, the case that must run and the case that must be excluded. The installer copies the event string without validating it against the harness's supported events. Use a documented event for each target harness. Do not assume an unknown key is safely ignored; its treatment is unverified.

The shared documented event names are `SessionStart`, `SessionEnd`, `UserPromptSubmit`, `PreToolUse`, `PermissionRequest`, `PostToolUse`, `SubagentStart`, `SubagentStop`, `Stop`, `PreCompact` and `PostCompact`. Event support alone does not make their input or output behavior identical.

Omit `matcher` when every occurrence should run. For `PreToolUse`, `PostToolUse` and `PermissionRequest`, it matches a tool name: `Bash` for shell calls, or `Edit|Write` for Claude Code's edit/write tools and Codex's `apply_patch`. Use `^Bash$` when the entire name must match; do not depend on unverified substring behavior. Both harnesses ignore the matcher on `Stop` and `UserPromptSubmit`. For finer conditions, inspect the event input in the command and return a non-blocking result for excluded cases.

## Command and result

The harness executes `command` as a shell string from the session's working directory and supplies one JSON object on standard input. On tool events, use `tool_name` and `tool_input`. The installer supplies no separate argument list. Do not ask questions or read human input; the input stream is already the event.

Use a command the session can resolve, such as an installed tool name. Paths are not resolved relative to the hook record. Other hooks on the same event can also run; this command cannot prevent them from starting. If the same executable is also called by an agent, follow [Tool](tool.md) for that interface while preserving the event-specific interface here.

Choose output for the event:

- To proceed without adding context, exit 0 and print nothing. On Claude Code this does not grant an outstanding tool permission.
- To block an event that supports blocking, exit 2 with the reason on standard error, or exit 0 with exactly one event-appropriate JSON object on standard output. An ordinary exit 1 is not a reliable block; Claude Code usually treats it as a non-blocking error, and Codex ignores plain text on `PreToolUse`.
- For a JSON denial on `PreToolUse`, use `hookSpecificOutput` containing `hookEventName: "PreToolUse"` and `permissionDecision: "deny"`. Use this shared form rather than the legacy top-level `decision: "block"` form. Codex also accepts the latter with a reason; Claude Code retains it as deprecated behavior.
- To add context, use `additionalContext` inside `hookSpecificOutput`, with the event name, only for an event that supports it. Shared supported cases include `SessionStart`, `SubagentStart`, `PreToolUse`, `PostToolUse` and `UserPromptSubmit`. Plain text is delivered on `SessionStart` and `UserPromptSubmit`, not `PreToolUse`.

A line before a JSON object can invalidate the result. Keep progress output off standard output. A `PostToolUse` result cannot undo an operation that already ran. On `Stop`, exit 2 asks the conversation or turn to continue; it does not reject the completed turn.

Set a positive timeout in seconds when the command might hang; omission uses the harness default. Some events impose their own limits, so verify the effective limit for the selected event. A timeout is not a blocking decision: on Claude Code, a timed-out `PreToolUse` command does not block the tool call.

The description is one line naming the event and action for a person listing hooks. It is not emitted into the executable hook configuration. Enforce the behavior in the command, not the description.

## Edit, convert and verify

Edit the source record and regenerate through [rbtv CLI](rbtv-cli.md). Changes to the description alone do not change execution. When converting another hook format, retain only a shell command and supported event behavior; route prompts, HTTP calls and agent launches back through the choice of kind.

Feed the command representative event JSON for a blocking case, an allowed case and an excluded case. Check its status and both output streams. Then test it in a real session that loads the generated settings. A session started above a Claude Code project may not load that project's settings. Codex runs a hook only when it holds a stored approval of that hook ("persisted hook trust" in Codex's help); the record cannot grant that approval. A Codex session that `cast` launches or resumes, and every Codex turn the Ignite waking service runs, runs hooks without that approval step, because [cast](../../../cast/capabilities/tools/cast/cast.md) and `ignite turn` pass Codex's `--dangerously-bypass-hook-trust` option. The cost is that any hook file in the launch folder runs unreviewed: read `.codex/hooks.json` before launching Codex through `cast`, or running an Ignite agent on Codex, in a folder whose content you did not write.

Installer acceptance checks the record's shape. It does not prove event support, matching, execution or blocking. Record which harnesses were actually exercised and leave untested behavior explicit.

## Template

Omit `matcher` for all occurrences. Omit `timeout` to use the harness default.

```json
{
  "name": "<name>",
  "description": "<event and action>",
  "event": "<supported event name>",
  "matcher": "<value this event matches>",
  "command": "<resolvable shell command reading event JSON>",
  "timeout": <positive whole number of seconds>
}
```
