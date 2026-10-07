# Task

A task specifies one launch's result, scope and completion criteria. The prompt supplies the standing method; the task supplies this instance's inputs and boundaries.

The recipient does not inherit the supplier's open files or full conversation. An Ignite turn may also receive memory, board content and recent channel messages, but those do not replace an explicit task.

## Supply the work

Read the receiving agent's [Prompt](prompt.md) and description to identify required inputs. Name accessible paths and values, not “the file we were reading.” Do not paste the supplier's prompt or restate the recipient's standing method.

Start with the result to produce, then use `## Scope` and `## Done contract` in that order. A task saved for later uses the same text in a file, not notes addressed to someone who remembers the conversation.

### Scope

State separately what the agent may examine and what it may change. Use closed lists of files, folders or records; write “no files” when appropriate. “Related files” and “as needed” leave the boundary undefined.

Keep one independently assessable result. If two sets of work can be accepted separately, split the tasks. Do not put completion checks in Scope or copy the agent's standing remit into it.

### Done contract

State observations a second reader can use to accept or reject the result. For an exact check, name the tool and passing result. For a judgment, name the evidence and criterion rather than asking whether the work “looks done.”

State the action on failure: stop and report the missing input or failed condition, or make a specified correction. “Retry” alone gives no next action. A noninteractive launch must not wait for a reply it cannot receive. Do not include the next launch's work or duplicate checks already required by the standing method.

## Deliver the task where the launch reads it

| Supplier | Where the task belongs |
|---|---|
| Person in conversation | The message, including accessible inputs |
| Parent agent | The launch text or task file supplied to the child |
| Slack-triggered work | The message, with the scope and inputs stated explicitly |
| Timer naming a board check | The named board entry, containing the result, scope and done contract |

A timer's check name alone is not the task. A board entry about another subject is not implicit scope. For a saved task, edit the file before launch; changing it after the agent has read it does not deliver the correction. Send a new task or correction through the supported continuation mechanism.

## Template

```markdown
<One result this launch produces.>

## Scope

Examine: <closed list of accessible inputs>
May change: <closed list, or no files>

## Done contract

<Observable acceptance criteria and exact checks.>
<What to do when an input is missing or a condition fails.>
```

## Review

Read the task beside its prompt without relying on the supplier's conversation. Classify a proposed action from Scope alone and a result from the done contract. Test a missing input. A successful launch proves only that text was supplied, not that the work was bounded.

When converting a ticket, put the result first, boundaries in Scope and acceptance criteria in Done contract. Classify standing instructions through [Choosing what to build](../methods/choosing-what-to-build.md). Preserve the task's requirements, not its old headings.
