# Choosing what to build

Choosing what to build is the decision of which kind of file carries the content, made before any entry is opened. The kinds are a capability exposed by one exposure method, a prompt and an agent, a tool, a hook, an MCP server, a folder artifact, a principle and a glossary entry. Outside rbtv a hook can be a prompt to the model. Here a hook is a command that a harness runs. The page "Exposure method"¹ says where a skill differs from a command. The page "Choosing where to build"² decides the module, the component and the mirror. This page does not decide those.

The decision is for an author who knows the content and does not yet know which kind carries it. Choose the kind so that the agent has the content when the work needs the content, and does not have the content when the work does not need it. Read this page before you open an entry, when the work is to create, to convert, or to review a kind that is not yet settled. Do not read this page to edit a file whose kind is already the one you are changing. Decide the kind from when the content is needed and from who can make it reach the agent then. Do not decide it from the word in the request. An entry says how to build the kind that this page gave. It does not choose the kind.

## How it fails

The rbtv CLI can accept the file that it installs, and the kind can still be wrong. The rbtv CLI installs a file because of the folder that contains it. The rbtv CLI does not read whether, with that kind, the content reaches the agent when the work needs it.

- The request said "skill", and a step has an exact answer. The agent estimates the answer. The rbtv CLI accepts the skill from its folder. It does not read the step.
- A tool is built, and no skill, rule or command says when to run it. The rbtv CLI places the tool on PATH. The agent does not know the tool is there.
- A capability is written, and no exposure method and no step of a prompt names it. The rbtv CLI installs a tool from the capabilities folder. It does not install the other pages there. The agent never reads the unnamed page.
- A method that the agent needs only when a point comes is pasted into a rule, or into folder instructions. Every task includes that method, including a task that never reaches that point. Every visit to the folder includes that method, including a search.
- Several capabilities of one purpose each get their own skill. The agent chooses among those descriptions before any work.
- An agent is built for a fixed checklist the caller could follow. The launch starts another context and returns what the caller could have produced.
- A rule tells the agent to run a check, and the agent skips the text. The check does not run. A hook is the only kind, and the action must also happen under OpenCode. OpenCode receives no hooks.
- A principle states how an agent behaves during a task. The harness does not present a principle. The agent never sees that sentence during the task. Or a file uses a term that no glossary entry defines, and each reader takes a different meaning.
- An index file lists the folder. rbtv has no index file for a folder. An agent that is sent to that file meets a list, and the instructions stay unread.

## How to do it

1. **The request's word, then the content and when it is needed.** The request's word, such as "skill" or "command", is a hint. It is not the kind. Find a task where the work came out wrong, or never started, because this content was absent. Find a second task where the same content would be wrong if it were present. That pair is the failure. The cause is that nothing gives the content to the agent on the first task and keeps it from the agent on the second. Write one sentence: what the content is, who needs it, and when. When you cannot name when, stop. The content is not ready to place.

   Weak: "The user asked for a skill, so the kind is a skill."

   Strong: "The content is the count of failing tests. The agent needs that count before it reports. The request asked for a skill."

   The weak line takes the request as the kind, so a later step never asks whether a tool prints the count.

2. **Name each file whose purpose already covers the content.** Search before you choose a new kind. The page "Single source of truth"³ says a fact has one home. When one file's purpose covers the content, change that file. Do not build a second kind for it. Name each file you considered, and why its purpose does not cover the content. When none covers it, choose the kind in the steps below. After the kind, the page "Choosing where to build"² decides the module, the component and the mirror.

3. **Ask whether a tool does the step, before any text.** Read the page "Deterministic first"⁴ for what an exact answer is. When you can name the answer that a CLI would print, and two runs of that CLI print the same answer, the step is a tool. A request that names a skill, a rule or a command does not make that step one of those. A decision, a weighing or a wording is not that answer. Do not write instructions that ask the agent to produce an exact answer. When a tool already produces it, name that tool in the text that says when to run it. Do not build a second tool. The page "Tool"⁵ says how the file is written.

   A tool does not say when to run it. The rbtv CLI places the tool on PATH and does not check that a skill, a rule or a command names it. After the tool, continue. Choose the exposure method that says when to run the tool. A judgment in the same request stays text. It does not move into the tool.

   Weak: "Write a skill that counts the failing tests and reports the number."

   Strong: "Build a tool that prints the count of failing tests. The skill says to run that tool before the report, and to take the number from the tool."

   The weak line asks the agent to estimate a count.

4. **Choose a hook when a command must run even if the agent ignores every text.** A hook is a command that a harness runs when an event happens. It is not an exposure method. The page "Exposure method"¹ names the four, and a hook is not among them. Choose a hook when you can name the event, the command has an exact result, and the agent could skip a rule that only asked for that command. Do not choose a hook for a judgment. The rbtv CLI writes hooks for Claude Code and Codex. OpenCode receives none. When the action must also happen under OpenCode, do not stop at the hook. Add the kind that reaches that harness: a rule, or a text that names the tool. The page "Hook"⁶ says how the file is written. The page "rbtv CLI"⁷ says what the rbtv CLI writes, and what it does not write for OpenCode.

   Weak: "Add a rule that says to run the linter before you finish."

   Strong: "Add a hook on the edit event whose command is the linter, because the agent can skip a rule that only asks for that run."

   The weak line depends on the agent noticing the text. The check does not run when the agent skips it.

5. **Choose an MCP server when the actions come from a server, not from one CLI on PATH.** A tool is one CLI that the rbtv CLI places on PATH. An MCP server offers the agent a set of actions through the protocol. The file names either a local command or an address, and it names the environment variables that contain the secrets, never the secret values. An MCP server is not an exposure method. Choose an MCP server when the harness should list those actions, or the server is reached at an address. Choose a tool when one local CLI returns the answer and the agent, or a hook, runs it by name. Do not write a skill that pastes the calls that a server should offer. The page "MCP server"⁸ says how the file is written.

   Weak: "Write a skill that calls the browser and reads the console."

   Strong: "The browser actions are a server the harness lists. Build an MCP server. The skill does not contain those calls."

   The weak line puts a server's actions in text the agent may never open.

6. **Choose the exposure method by who decides that the text reaches the agent.** Read the page "Exposure method"¹ before you choose among a skill, a command, a rule and folder instructions. It says who decides for each. Choose the kind whose deciding party gives the content to the agent on the first task of step 1 and not on the second.

   Do not choose a skill because a person would type its name. Do not choose a rule because the words say the content always applies. Choose a rule when the agent would not open a skill for the point, and the line is not false outside one folder. Do not choose folder instructions for a line that would still be true in another folder. When the agent must also start the work, and no person types a name, do not leave that work only in a command. That work needs a skill or a rule as well, or instead.

   A correction of one agent's behaviour, learned from its runs, is not a rule you write. The dreamer writes that file. The page "Learned rules"⁹ says so. Do not build a skill or a rule for that correction.

   Then open the page of the kind. The page "Skill"¹⁰, the page "Command"¹¹, the page "Rule"¹² or the page "Folder instructions"¹³. The page "Rule"¹² says when the rule is loaded, and when the agent acts on the rule.

   Weak: "The tone guide always applies, so the rule's body is the guide."

   Strong: "The tone guide is needed before a message to a client. The agent would not open a skill for a short message. A rule names the tone-guide capability. The guide is not the rule's body."

   The weak line puts the guide on every task, including a task that sends no message.

7. **Pair a capability with that exposure method, or with a step of a prompt.** The kind is a capability when work remains after the exposure method has been followed. One case is a second route that might name that work. The other case is a method that only some readings of the exposure method need: written there, every reading would contain it. The exposure method names the file, as the page "Entry point"¹⁴ says. When the whole content is one short method, and no second route needs it, leave it in the exposure method. Do not add a capability for those lines. Do not choose a capability with no route. The rbtv CLI does not install that file, so the file never reaches an agent.

   A step of a prompt may name a capability. That step does not replace an exposure method when the content must also reach other agents. The page "Entry point"¹⁴ says what a prompt is not. The page "Capability"¹⁵ says how the file is written.

   When the content is more than one capability, read the page "Nested exposure"¹⁶ before you write one skill, one rule or one command for each. That page says when one exposure method covers the set. A pack is a named list of files already chosen. Turning it on installs those files together. It does not make a capability reach an agent. Do not build a pack in place of that exposure method.

   An index file is not a kind: rbtv has no file whose only job is to list the files of a folder. When the files are needed at different times, follow the page "Entry point"¹⁴.

   Weak: "Write the method as a capability. The agent will find the file."

   Strong: "Write the method as a capability. The rule's row names that file."

   The weak line leaves the page uninstalled.

8. **Choose an agent only when the work cannot stay in the caller's context.** The same prompt must take a different task on each launch. The page "Agent"¹⁷ says what the caller cannot keep, and the two ways the rbtv CLI places the folder. When the caller's own job already covers the work, the kind is not an agent. A fixed checklist is not an agent. It is a skill, a command, or a capability that the skill or the command names. Do not choose an agent in order to expose a capability. The page "Exposure method"¹ says an agent is not one of the four.

   Choose a prompt when you are writing the agent, or when that agent exists and its prompt is what is wrong. Do not choose a prompt as the way that a capability reaches other agents. The page "Prompt"¹⁸ says how that text is written. Sections of the prompt, and sections of the task, are chosen on that page. They are not kinds this page chooses.

   Weak: "Build an agent that runs the checklist on each file."

   Strong: "The checklist stays in the caller's context. Build a skill whose row names the checklist capability."

   The weak line starts another context for work the caller could do.

9. **Choose a folder artifact when only some work in one folder needs the file.** Folder instructions are the exposure method for a line that would be false in another folder. A line that every reading of that folder needs stays in those instructions, as the page "Folder instructions"¹³ says. Content that only some work in that folder needs is a folder artifact, and the folder instructions name it. Content that is true for one kind of file in every folder is not a copy in each folder: choose a skill or a rule for it, as step 6 says. The page "Folder artifact"¹⁹ says how the file is written.

   Weak: "Put the review steps in the folder instructions, so every visit follows them."

   Strong: "The review steps are a capability. Folder instructions name that file when the agent edits, and a search does not follow the steps."

   The weak line makes a search follow steps it does not need.

10. **Choose a principle or a glossary entry when the content is not for one task.** Choose a principle when the content shapes how a thing of rbtv is built, whatever its kind, and no principle already decides it. An instruction about how an agent behaves during a task is a rule, not a principle. The page "Principle"²⁰ says how the file is written. Choose a glossary entry when the content is what a term means, or how to build the thing that the term names. Before any file uses a new term, write the entry. A term that a file uses, and that no entry defines, means something different to each reader. The page "Terminology is king"²¹ says the entry is that term's one file. The page "Writing a glossary entry"²² says how the entry is written. A principle and a glossary entry are capabilities. They are not exposure methods. The route that already sends a builder to them names them. Do not write a skill whose only job is one principle, or one entry.

    Weak: "Write a principle: before you commit, write the cause."

    Strong: "Before a commit, writing the cause is conduct during a task. Write a rule. A principle shapes how a file is built, and the harness does not present it during the commit."

    The weak line puts the sentence where the harness does not present it, so the agent commits without the cause.

- When you edit: do not use this page to change the text of a file whose kind is already the one you are changing. When the edit shows the kind was wrong, stop and start again at step 1. The rbtv CLI does not ask whether the folder still matches the content.
- When you convert: decide each part here before you open its entry. The page "Exposure method"¹ says what to do with an outside file that is both a typed name and a description. A step with an exact answer becomes a tool, not a paragraph of the skill. A hook in the source that is a prompt to the model is not a hook here.
- When you review: start from when the content is needed, not from the folder that the file sits in. A review that only checks that the rbtv CLI accepts the file misses a skill that should have been a tool, and a rule that should have been a hook.

Checks:

- A reviewer sees one sentence that names the content, who needs it, and when. The kind is the one that the steps give. It is not the word in the request, unless that word is the kind that the steps give.
- A step with an exact answer is a tool, and a skill, a rule or a command says when to run it. A capability has an exposure method that names it, or a step of a prompt that names it. No file is an index of its folder. An agent is not a checklist. A hook is not the only kind when the action must also happen under OpenCode.
- The rbtv CLI accepts the file. Acceptance shows the folder was recognized as that kind. It does not show that, with that kind, the content reaches the agent when the work needs it. The page "rbtv CLI"⁷ says what acceptance shows.
- Give an agent a request that says to build a skill for a count, a date or a format, and the files of the component. The result is a tool, and a text that says when to run it. If a skill is written, it does not ask the agent to produce that answer.

## References

| # | Page | File | Read | When | To |
|---|---|---|---|---|---|
| 1 | Exposure method | [Exposure method](glossary/exposure-method.md) | when | choosing among a skill, a command, a rule and folder instructions, or converting a file that is both a typed name and a description | take who decides for each, and that an agent, a hook, an MCP server, a tool and a prompt are not among the four |
| 2 | Choosing where to build | [Choosing where to build](choosing-where-to-build.md) | when | the kind is chosen and the file has no home yet | decide the module, the component and the mirror |
| 3 | Single source of truth | [Single source of truth](principles/single-source-of-truth.md) | when | searching for a file whose purpose already covers the content | take that a fact has one home |
| 4 | Deterministic first | [Deterministic first](principles/deterministic-first.md) | when | a step might have an exact answer | take what an exact answer is, and that a tool must be reachable from a skill, a rule or a command |
| 5 | Tool | [Tool](glossary/tool.md) | when | the step has an exact answer and no tool produces it | write the tool |
| 6 | Hook | [Hook](glossary/hook.md) | when | a command must run on an event even if the agent ignores every text | write the file; a hook is not an exposure method |
| 7 | rbtv CLI | [rbtv CLI](glossary/rbtv-cli.md) | when | the rbtv CLI is to accept the file, or a hook must also be judged for OpenCode | take what acceptance shows, and that OpenCode receives no hooks |
| 8 | MCP server | [MCP server](glossary/mcp-server.md) | when | the actions come from a server the harness should list | write the file; an MCP server is not an exposure method |
| 9 | Learned rules | [Learned rules](glossary/learned-rules.md) | when | the content is a correction of one agent's behaviour, learned from its runs | leave that file to the dreamer |
| 10 | Skill | [Skill](glossary/skill.md) | when | the exposure method is a skill | write the skill |
| 11 | Command | [Command](glossary/command.md) | when | the exposure method is a command | write the command |
| 12 | Rule | [Rule](glossary/rule.md) | when | the exposure method is a rule | write the rule |
| 13 | Folder instructions | [Folder instructions](glossary/folder-instructions.md) | when | the exposure method is folder instructions, or a line might belong in that file rather than in an artifact | write that file, and take which line stays in the body |
| 14 | Entry point | [Entry point](glossary/entry-point.md) | when | a route will name a capability, or a file would only list other files | take how a row names a file, and what a prompt is not |
| 15 | Capability | [Capability](glossary/capability.md) | when | work remains after the exposure method, or a second route might name it | write the capability |
| 16 | Nested exposure | [Nested exposure](nested-exposure.md) | when | the content is more than one capability | take when one exposure method covers the set, after the kind is chosen |
| 17 | Agent | [Agent](glossary/agent.md) | when | the work cannot stay in the caller's context | write the agent, and take the two placements |
| 18 | Prompt | [Prompt](glossary/prompt.md) | when | the agent is chosen, or an existing agent's standing text is what is wrong | write the prompt, and choose its sections there |
| 19 | Folder artifact | [Folder artifact](glossary/folder-artifact.md) | when | only some work in one folder needs the file | write the artifact |
| 20 | Principle | [Principle](glossary/principle.md) | when | the content shapes how a thing is built, whatever its kind | write the principle |
| 21 | Terminology is king | [Terminology is king](principles/terminology-is-king.md) | when | a file will use a term | take that the glossary entry is the term's one file |
| 22 | Writing a glossary entry | [Writing a glossary entry](writing-a-glossary-entry.md) | when | the content is what a term means, or how to build the thing the term names | write the entry |
