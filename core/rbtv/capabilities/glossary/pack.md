# Pack

A pack is a named list of files that a component declares, so that an installation or an agent turns those files on together. Outside rbtv the nearest thing is a package or a plugin: a folder of files copied together. In rbtv the files stay in the components that own them. The pack names each file by its id.

A pack is for one group of files that more than one target must receive together, written in one file, so the copies of that list do not drift. An author wants one when the same group must be turned on for more than one target: several agents, or an installation and an agent. A group that one target needs, and that no second target will turn on, is that target's own list. The ignite component declares the pack that every Ignite agent turns on, so those agents receive the same files and one name turns that group off. That pack names files that other components own, and those files stay in those components. Write a pack so that each target which turns it on receives the same files. A target which must not have one of those files does not turn it on.

## How it fails

The program can accept a pack, and the pack can still fail. It checks each name against a file that it installs. It does not read whether every target that turns the pack on needs that file.

- The pack is declared for one target. The list is not in that target's record. Only the pack's name is there. A later turn-on installs every file for a target that did not need them. The one target's record does not show the files.
- A file that only some of those targets need is in the list. Every turn-on installs it. A skill or a rule in that list puts its text in front of an agent that does not do that work.
- The description names the kinds of file in the list, or names the files, and does not say what the group is for. A later author adds a file that matches those words and that the targets do not all need.
- An agent folder is in the list. Turning the pack on does not place that folder. The turn-on writes a sub-agent file only when the run also names that agent with `--on`, or settings for it were recorded by an earlier run. The agent the list was meant to include does not arrive by the pack.
- A file that a target must keep after the pack is turned off is only in the pack. Turning the pack off removes that file, because the target did not list it and no other pack that is on names it.

## What it is composed of

The author writes one file, in the component that declares the pack. The page "rbtv command"¹ says the name of that file and the folder that the program reads. The program checks the file against the schema [pack.schema.json](../templates/pack.schema.json). This page does not list the fields.

The description is always there. It is one line that says what the group is for. A person who lists packs reads that line. The program does not copy it into a file that an agent reads. The page "rbtv command"¹ says the program writes no file for the pack, so the description is not a decision about what an agent loads.

The list is always there. Each entry is the id of a file that the program installs, written as `module/component#name`. The part after `#` is the name that the program installs, not a short name and not a path. The list may name a file of another component. The page "Choosing where to build"² says which component declares the pack, and what a mirror folder does to a file that the list names.

## How to build it

1. **Name the targets that share the group, then the purpose.** Name those targets before you write a line of the pack. The failure is two targets that should have the same files and do not, because each record keeps its own copy of the list. The cause, for a pack, is that the group is written in more than one record, or is not written as one list at all. The situation is those targets, and one further target that must not receive one of the files. Then write the purpose from that failure: one list, turned on by one name, so each of the sharing targets receives the same files, and the further target does not turn the pack on. An author who starts from the files of one agent writes a list that belongs in that agent's record.

   Weak: "This agent needs these skills, so the pack lists them."

   Strong: "Three agents need the same files for a Slack turn. A research agent must not receive the Slack rule. The pack is the list those three turn on."

   The weak line declares a pack for one target. A later turn-on installs every file for a target that did not need them.

2. **Put in the list only a file that every such target needs.** Put a file in the list when every target that turns the pack on needs that file. A file that only some of them need stays out. It goes in that target's own list, or in a second pack that only those targets turn on. The page "Agent"³ says what an agent's record may list. Read it for the placement that installs a pack named in that record. A skill or a rule in the list puts its text in front of every agent that turns the pack on. The page "Progressive disclosure"⁴ says why text that an agent does not need should not be in front of it.

   Write each id as `module/component#name`, because the program matches that string to a file that it installs. A short name is not that string. Name a skill, a rule, a command, a hook, an MCP server, a tool, or folder instructions. When the list names a hook, read the page "rbtv command"¹ for which harness receives a hook file. A target on a harness that receives none does not get that hook.

   Weak: "`meta/communication#slack-message-format` in a pack that a research agent and an Ignite agent both turn on."

   Strong: "Leave `meta/communication#slack-message-format` out of that pack. The Ignite agents turn on a pack that names it. The research agent does not."

   The weak line puts the Slack skill in front of the research agent.

3. **Do not name a file that the turn-on does not install.** Do not name a capability. The program does not install that file. The page "Choosing what to build"⁵ says a pack does not make a capability reach an agent. Do not name a whole-folder skill. Its id is not the id of a file that a component installs, so the scan refuses that name. Do not name another pack.

   Do not name an agent folder. Turning the pack on does not place that folder. The page "Agent"³ says the two placements. A pack that names an agent writes a sub-agent file only when the run also names that agent with `--on` and a harness, a model and an effort, or when an earlier run recorded those for it. The pack file cannot carry them. Without them the turn-on writes no file for that agent.

   Weak: "`core/ignite#reviewer` in the list, so turning the pack on places that folder. The page "Agent"³ says how to place the folder."

   Strong: "`core/ignite#agent-controls` in the list, so turning the pack on installs that skill. The page "Agent"³ says how to place the folder."

   The weak line names an agent folder. The turn-on alone writes no file for that agent.

4. **Name a file that another component owns by its id.** The declaring component is the one whose work the group serves. The page "Choosing where to build"² says how to find it. A file that the group needs can sit in another component. Write that file's id. Do not copy the file into the component that declares the pack. The pack is a list, not a second home for the file. The page "Single source of truth"⁶ says why a second copy drifts. The ignite pack names files that other components own. Those files stay in those components.

5. **Write the description as what the group is for.** Write one line. A later author reads it to decide whether a file belongs. A person who lists packs reads that line after the name of the component that declares the pack. Do not start the line by naming that component. Do not list the files. The program does not copy the line into a file that an agent reads, so the line is not a load decision.

   Weak: "Skills and a rule for Slack and documents."

   Strong: "The files every Ignite agent needs for a Slack turn."

   The weak line names kinds. A later author adds any Slack skill.

6. **Choose a name no other pack has.** Do not write the name inside the file. The page "rbtv command"¹ has it as the file name. The program keeps one pack for each file name, across every component. Choose a name that says which targets turn the pack on. A name that does not say which targets share the group is accepted, and a later author turns the pack on for the wrong target.

   Weak: "tools"

   Strong: "ignite-slack"

   The weak line does not say which targets turn the pack on.

7. **Change a named id in the same change as the move or the rename.** The id is a string. The program matches it to a file that it installs. It does not follow the file. A move to another component changes the module and the component in the id. A rename of the file changes the name after `#`. Change that string in the pack in the same change. The program does not rewrite the list. The page "Choosing where to build"² says what a mirror folder does when it leaves out a file that a pack names.

8. **Leave out a file that must remain after the pack is turned off, unless the target also lists it.** The target records the pack's name, not a copy of the list. Turning the pack off removes that name. It removes a file that the pack was the only reason for. It leaves a file that the target lists itself. It leaves a file that another pack still on also names. A file is installed once, however many lists name it. Removing a file by its name, while a pack that names it is still on, does not remove the file. The pack stays the reason until the pack is turned off.

   Do not put a file only in the pack when the target must keep that file after the pack is turned off. The pack cannot record that exception. The target lists the file itself, or the file stays out of the pack. Turning the pack off does not delete the pack file, and it does not remove the target. An agent's folder, and the files that agent created, stay. Turning the ignite pack off leaves the agent folder.

   If turning either of two packs off should remove a file, name that file in only one pack, and do not have the target list it. A file named by two packs that are both on stays when one of them is turned off.

   Weak: "The standing rule must remain, and only the pack names it."

   Strong: "The standing rule is in the pack, and the agent lists that rule itself, so turning the pack off leaves the rule."

   The weak line loses the rule when the pack is turned off.

- When you edit the list, change the pack file. It is the only copy of the group. A target that already has the pack on still has the files of the old list until the run that rewrites installed files. The page "rbtv command"¹ says which run that is. Renaming the pack file makes a new name. A target that had the old name on does not follow the rename. On that run, an installation drops the old name, and a file that only the old name installed is removed, unless the target lists the file or another pack that is on names it. An agent is refused on that run, `pack-unknown`, until its record names the new name.
- When you convert an outside list of files to install together, put in the pack only a file that the program installs, under the id that the program matches. A part that is instructions, or another kind of file, does not become a line of the list. The page "Choosing what to build"⁵ says where that part goes.
- When you review a pack, do not stop when each name matches a file. For each file, name the targets that turn the pack on, and confirm that each of them needs that file. Confirm that a file which must remain after turn-off is not only in the pack.

Checks:

- Every id names a file that every target which turns the pack on needs. The description says what the group is for, in one line, and does not list the files. The list has no agent folder and no capability. A file that must remain after the pack is turned off is also in a target's own list, or is not in the pack. The name is not the name of another pack.
- A pass shows that each name matched an installed file. It shows that the description is present. It shows that the name is one pack in the catalog. It does not show that every target needs every file. It does not show that turning the pack off leaves what must remain. The page "rbtv command"¹ says how to read a pass.
- Turn the pack on for two targets that should share the group, and look at one target that should not have one of the files. That third target must not receive the file. Then turn the pack off for a target that also lists one file itself. That file remains. A file that the pack was the only reason for is gone.

## Template

```json
{
  "description": "<what the group is for, in one line, for every target that turns the pack on>",
  "files": [
    "<module>/<component>#<name the program installs>"
  ]
}
```

## References

| # | Page | File | Read | When | To |
|---|---|---|---|---|---|
| 1 | rbtv command | [rbtv command](rbtv-command.md) | when | writing the file, reading a pass, naming a hook, or updating a target that already has the pack on | take the file name and the folder, what a pass shows, which harness receives a hook file, and which run rewrites installed files |
| 2 | Choosing where to build | [Choosing where to build](../choosing-where-to-build.md) | when | deciding which component declares the pack, or a named file may sit in a component that a mirror replaces | take the component, and what a mirror folder does to a file that the list names |
| 3 | Agent | [Agent](agent.md) | when | a file would be an agent folder, or a target's own list should name a file that the pack must not be the only reason for | take the two placements, what a record may list, and which placement installs a pack from that record |
| 4 | Progressive disclosure | [Progressive disclosure](../principles/progressive-disclosure.md) | when | a file in the list would put text in front of an agent that does not do that work | take why that text should not be in front of that agent |
| 5 | Choosing what to build | [Choosing what to build](../choosing-what-to-build.md) | when | the list would name a capability, or a converted part is another kind of file | take that a pack does not make a capability reach an agent, and where that part goes |
| 6 | Single source of truth | [Single source of truth](../principles/single-source-of-truth.md) | when | a file that the group needs sits in another component | take why a second copy of that file drifts |
