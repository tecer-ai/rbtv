# Agent parity

Agent parity is the requirement that an agent can take every action that a human can take on state that software manages. The human takes the action through a screen or a guided flow. The agent takes it in a form that can be run again and that asks no question: that form is the agent path. The requirement applies even when a control that only a human can use would ship sooner.

An action only a human can take makes an agent wait for a human. An action with no form that can be run again leaves the next agent without the steps. The page "Context window"¹ calls that context gap: the model invents a step it was not given. An agent that drives the screen a human uses fills the context window with screens the task does not need. That page calls it context load. When both reach the same operation through their own interfaces, either can do the work, and the results match.

Apply this whenever you add or change a control on state that humans and agents both use. The state includes what rbtv manages, and it includes any other software both use. Apply it so that an agent completes the action with no human present, and a later run of the same form leaves the same state.

## How it fails

The program can accept the software, and an agent can still be unable to take an action a human can take. The program does not check whether an agent can take the action.

- The human control ships, and the agent path is left for later. The agent waits for a human.
- The agent path is the human interface. The agent clicks through the screen, or it answers the questions a guided flow asks. The action cannot be run again from a record of it, and the context window fills with screens the task does not need.
- The agent path does not perform the action. It prints the steps a person follows, or it leaves different state from the human path. The results do not match.
- For state rbtv manages, the agent edits a file a person sees, and the action does more than that edit. Or the agent edits a copy the program writes. The action the human took is not done.
- A control only a human can use is the normal route, and no exception is written. Every agent drives the screen.

## How to apply it

1. **Name each human action, and write the agent path in the same change.** The failure is an action a human can take on managed state that an agent cannot take without a human. The cause is a control built for a human first, because that control can be tried today. The situation is when you add a screen, a guided flow, or a click. List those actions. For each, write the agent path before you ship the human control. Shipping the control alone is the trade-off this principle refuses.

   Weak: "The person installs a component from the screen. An agent can drive the screen until an invocation exists."

   Strong: "The person installs a component from the screen. In the same change, the agent installs that component by an invocation that names it, and the screen calls that install."

   The weak line makes driving the screen the route, so the agent waits or reconstructs the clicks.

2. **Give the agent a form that the agent can run again without a question.** When the action is an edit of a file a human edits, the form is that file. When the action does more than change that file, such as writing other files or starting a program, the form is an invocation of the tool that performs the operation. The page "Tool"² says what a tool is. The invocation carries every input. When an input is missing, it stops and names what the next invocation has to carry. It does not ask. Driving the screen is not this form. The next run has no record of the clicks, which is context gap. The screens are in the context window, which is context load. Decide what carries the invocation with the page "Choosing what to build"³. Follow the page "Deterministic first"⁴ when the operation has an exact answer, and when the next agent has to learn when to call the tool.

   Weak: "The guided flow asks the person. The agent path asks those same questions."

   Strong: "The guided flow asks the person. The agent path takes those answers as arguments and asks nothing. A missing argument stops and names the next invocation."

   The weak line still needs a person, or it fills the turn with questions the invocation could have carried.

3. **Both paths perform the action, and the state matches.** Follow the page "Single source of truth"⁵ for one implementation of the operation. After the human path and after the agent path, the state is the same, and the agent path performed the action. A path that prints the steps a person follows does not perform it.

   Weak: "The invocation prints the steps of the install. The screen performs the install."

   Strong: "The invocation performs the install. The screen calls that install. After either path, the installed set is the same."

   The weak line leaves the action to a human.

   The install of rbtv has this shape. Its guided flow asks a person, then calls the install operation. The invocation that performs the install calls the same operation and asks nothing. The page "rbtv command"⁶ says how the program is run.

4. **For state rbtv manages, match the path to what completes the action.** That state is components, agents, settings, runtime data, memory, and folder artifacts. When the action is the edit of a file a human edits, the agent edits that file. When the action does more than the edit, such as the program writing the files a harness loads, the agent runs the tool, and the human control calls that tool. Do not have the agent edit a copy the program writes. The page "rbtv command"⁶ says what the program writes. Follow the page "Single source of truth"⁵ for that copy.

   Weak: "The person runs the add. The agent edits the copy the program writes for the harness."

   Strong: "The person runs the add. The agent runs the same add, with the name in the invocation. Neither edits the copy the program writes."

   The weak line does not perform the action the human performed by running the program.

5. **Write the exception when a control has no operation an agent can invoke.** A graphical action with no such operation is an exception. Write the action, why no agent path exists, and that the agent reaches it by driving the screen. Driving the screen is computer use: the agent clicks and types in the interface a human uses. Do not make computer use the route for an action that has an operation. An exception that is not written is a human-only action, and the agent waits.

   Weak: "The color picker has no operation an agent can invoke. An agent drives the screen for every action on this state."

   Strong: "The color picker has no operation an agent can invoke. Stated exception: an agent drives that screen. Every other action on this state has an agent path that does not drive the screen."

   The weak line makes computer use the normal route.

When you edit, a new human control is a new action. Apply step 1 in the same change. The program does not ask whether an agent path exists.

When you review, list the actions a human can take on the state. For each, name the agent path, or the written exception. A review that only uses the human control misses an action the agent cannot take.

Checks:

- A reviewer sees, for each action a human can take on the state, an agent path that performs that action without a question, or a written exception that names the action and says the agent drives the screen. After both paths, the state matches. No path drives the screen for an action that has an operation.
- The program can accept the software. Acceptance does not show that an agent can take the action, or that the two paths leave the same state.
- Give an agent the state and one action a human can take, and not the screen. The agent completes the action. Then remove the agent path and give the action again. If the agent waits, or drives the screen, the path was not there.

## References

| # | Page | File | Read | When | To |
|---|---|---|---|---|---|
| 1 | Context window | [Context window](../glossary/context-window.md) | when | judging a path that drives a screen, or a path with no record of the steps | take context load, context gap, and what the model does when a step was not given |
| 2 | Tool | [Tool](../glossary/tool.md) | when | the action does more than an edit of a file a human edits | take what a tool is, and that the operation runs outside the context window |
| 3 | Choosing what to build | [Choosing what to build](../choosing-what-to-build.md) | when | deciding what carries the invocation | decide the kind |
| 4 | Deterministic first | [Deterministic first](deterministic-first.md) | when | the operation has an exact answer, or the next agent has to learn when to call the tool | take the decision for an exact answer, and the decision for how the next agent learns to call the tool |
| 5 | Single source of truth | [Single source of truth](single-source-of-truth.md) | when | both paths must perform one operation, or the agent path would edit a copy the program writes | take how one operation stays one implementation, and what to do with a copy |
| 6 | rbtv command | [rbtv command](../glossary/rbtv-command.md) | when | the action is one the program performs, or you are about to write how to run it | take what the guided flow and the install invocation do, and how to run the program |
