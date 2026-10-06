# Agent parity

Every action a human can take on software-managed state must also have a path an agent can execute without a human answering questions. Provide that path in the same change as the human control, even when shipping the control alone would be faster.

The agent path must perform the action and leave the same state as the human path. Printing instructions for a person does not satisfy this requirement. Both paths call one implementation, as [Single source of truth](single-source-of-truth.md) requires.

## Choose the agent path

If the entire action is an edit to a file that a human edits, the agent can edit that file. If the action also generates files, starts software or performs other operations, provide an invocation that completes the action. The invocation carries all inputs; missing input stops with the next required invocation, without asking or waiting. Follow [Tool](../glossary/tool.md) for the interface and [Deterministic first](deterministic-first.md) for exact work.

This applies to components, agents, settings, runtime data, memory and folder artifacts managed through rbtv, as well as other software humans and agents share. Editing a generated harness file is not an alternative to running the operation that generates it. [rbtv CLI](../glossary/rbtv-cli.md) identifies those operations and files.

Driving the human interface is an exception for a graphical action with no invocable operation. Document the exact action, why no agent path exists and how the agent uses the interface. Do not extend that exception to neighboring actions that do have operations. Reconstructing clicks and interpreting screens spends context on work that a direct invocation can avoid.

## Verify parity

List the human actions affected by the change. For each, identify the noninteractive agent path or its documented graphical exception. Exercise the human and agent paths from equivalent starting state and compare the resulting state. Give an agent an action without the human screen and confirm that it can complete it through the declared path.
