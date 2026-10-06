# Exposure method

An exposure method is how the content of a capability¹ reaches an agent. In rbtv the exposure methods are a skill, a command, a rule and folder instructions, and no other file. Every exposure method is an entry point, and the page "Entry point"² says what such a file contains and how its body is written. Outside rbtv that grouping is not used. A skill, a command, a rule, folder instructions, an agent, a hook and an MCP server are separate ways to extend an agent. In Claude Code a person can invoke a skill by typing its name, the same way as a command, and a command file works the same way as a skill.

A skill reaches the agent when the agent matches its description, before the agent has read the body. The rbtv CLI copies that description into the file that the harness shows, and the body of that file tells the agent to read the source. Claude Code also allows a person to type the skill's name, and it treats a command file the same way as a skill. rbtv does not use that path for a skill: a person who types a name uses a command. OpenCode shows the name and the description, and the agent loads the skill when it needs the content. A command reaches the agent when a person invokes its name, before the agent has read the body. On Codex the installed file has no description, only the instruction to read the source, so the name is what the person has. A rule reaches the agent because the rule is installed, on every task of every agent that has the rule, and the agent does not choose it. The rbtv CLI copies the rule for Claude Code, and Claude Code loads that text at the start of the session. For Codex and OpenCode the rbtv CLI places the body, without the frontmatter, in the root instructions file, which those harnesses load on every turn. The load is not the action. Folder instructions reach the agent because of the folder, only as far as the harness loads that folder's file. The rbtv CLI places the body, not the frontmatter, in that file. Claude Code loads a root file at the start of the session, and a file in a subdirectory when it reads a file there. Codex reads the instructions files from the project root down to the working directory at the start of a run, and stops when their combined size reaches the limit the rbtv CLI sets.

An agent is not an exposure method, in either placement. A hook, an MCP server and a tool are not exposure methods. A prompt is not an exposure method, and it is not an entry point. A step of its procedure may still send the agent to a capability.

An exposure method lets a capability reach the agent on the task where the work needs it, and keeps the capability absent on a task where the work does not need it. An author wants one when a capability has no way to reach an agent, or reaches an agent through a file that lets the wrong party decide. The page "Choosing what to build"³ decides which of the four to write, and reads this page for who decides for each. Write an exposure method for the party who decides for that kind, the party who can make the capability arrive.

## How it fails

The rbtv CLI can accept a skill, a command, a rule or folder instructions, and the capability can still fail to reach the agent, because the rbtv CLI does not read which party the file lets decide.

- The file is written for a party that the kind does not give the decision to. A skill written as a name a person types does not open, because the agent matches the description and may never type the name. A rule whose full text only some tasks need crowds every task, because that text is already loaded. Folder instructions written for every task miss the tasks that never enter the folder, because they arrive only as far as the harness loads that folder's file. A command whose needed facts are only in the body asks for them too late, because the person has already invoked.
- The capability is exposed through an agent, a hook, an MCP server or a tool. The rbtv CLI installs those. The capability's text does not arrive by a skill, a command, a rule or folder instructions.

## What it is composed of

The author writes no file named for an exposure method. The exposure method is a skill, a rule, a command or folder instructions, and that file is an entry point whatever the body contains. The page "Skill"⁴, the page "Rule"⁵, the page "Command"⁶ and the page "Folder instructions"⁷ name the file and the folder.

## How to build it

1. **The party who decides, then when the content reaches the agent.** The page "Choosing what to build"³ has already chosen which of the four. Name the party who decides for that kind, from the four above. Name the capability that should arrive, and read the page "Capability"¹ for what that file is. The failure is a capability absent when the work needs it, or present when the work does not. Its cause is that no file lets that party decide, or that the file lets a different party decide. The situation is one task where the capability should be in front of the agent, and a second task where it should not. Write what this exposure method does so that the capability arrives on the first task and not on the second. Read the page "Entry point"² for the file.

   Weak: "Use this when the person types the skill name."

   Strong: "The agent opens this skill when the task is a brand book and no name is written yet."

   The weak line writes the skill for a person. The agent matches the description and may never type the name, so it does not open the skill.

When you edit, change the kind when the party who should decide has changed. The kind is that party. A change of what the file contains is a change to the entry point, and the page "Entry point"² has it.

When you convert, take an outside file in which a person types the name and an agent also loads it from a description as two decisions. Decide each with the page "Choosing what to build"³. Do not leave both in one file. The rbtv CLI writes a skill and a command as different files, and it does not split one source into both. A hook, an agent, an MCP server or a tool in the source is not an exposure method.

When you review, name the party who can make the content arrive, and name the task on which it arrives. A review that starts from the body judges the entry point. It misses a kind that lets the wrong party decide.

Checks:

- A reviewer sees one of the four, and the party who decides is the party that kind gives the decision to. An agent, a hook, an MCP server and a tool are not the way the capability arrives. A prompt is not among the four.
- The rbtv CLI accepts the file. The page "rbtv CLI"⁸ says how to have it accepted. Acceptance shows the file was recognized as that kind. It does not show that the party who decides is the one that kind gives the decision to.
- Give the exposure method, once the rbtv CLI has accepted it, to an agent, with one task where the capability should arrive and one where it should not. Look at whether the capability arrives on the first and not on the second. For a rule, look at whether the text is present on both tasks and acted on only where it applies.

## References

| # | Page | File | Read | When | To |
|---|---|---|---|---|---|
| 1 | Capability | [Capability](capability.md) | when | naming what the exposure method lets arrive | take what a capability is |
| 2 | Entry point | [Entry point](entry-point.md) | when | writing the file, or editing what the file contains | take what the file contains and how its body is written |
| 3 | Choosing what to build | [Choosing what to build](../choosing-what-to-build.md) | when | before this page is opened, or a converted part is not one of the four | choose the exposure method, or place the part that is not one |
| 4 | Skill | [Skill](skill.md) | when | the exposure method is a skill | take where the skill file sits, and what a skill adds |
| 5 | Rule | [Rule](rule.md) | when | the exposure method is a rule | take where the rule file sits, and what a rule adds |
| 6 | Command | [Command](command.md) | when | the exposure method is a command | take where the command file sits, and what a command adds |
| 7 | Folder instructions | [Folder instructions](folder-instructions.md) | when | the exposure method is folder instructions | take where that file sits, and what folder instructions add |
| 8 | rbtv CLI | [rbtv CLI](rbtv-cli.md) | when | the rbtv CLI is to accept the exposure method | take what acceptance shows for this kind, and what it does not show about the party who decides |
