# Nested exposure

Nested exposure is several capabilities¹ exposed through one exposure method². Plain exposure is one exposure method for the content of one capability. The exposure methods are a skill, a command, a rule and folder instructions. The page "Entry point"³ names the same four things. An agent is not an exposure method, in either placement. A prompt is not an entry point. Outside rbtv, extra files sit in one skill's folder and are not separate skills. Here those files are capabilities. Any of the four that exposes several capabilities is an entry point, whatever the body contains.

Ten capabilities under plain exposure put ten descriptions, ten rule bodies or ten folder-instructions files in front of the agent. Nested exposure puts one of those in front of the agent. The agent chooses the capability only after that load. "Nested" means the capabilities are one level below what is exposed. An author reads this page when several capabilities share a purpose or the same documents. Write the nesting so that the agent meets one exposure method for the set, and opens a capability only after that load, for the case the row names.

## How it fails

The rbtv CLI can accept the skill, the rule, the command or the folder-instructions file, and the nesting can still fail. It installs a file in the skills folder, the rules folder or the commands folder. It does not install a page in the capabilities folder. It does not read the table.

- Each capability also has its own skill, rule or command. The agent meets a description or a body for each, so the one method does not shorten that list.
- A row names a skill, a rule, a command or folder instructions. An exposure method sits inside an exposure method. The agent loads one to find another. The rbtv CLI does not read the row.
- Capabilities the reader must separate before any load are nested. Each would need a description that names the other as the load to refuse, and the reader can match that sentence before either load. After the load, the one method matches the neighbor's job, or it hides a job of the set.
- A rule or folder instructions paste every capability into the file that is read on every task, or on every visit to the folder. Every task pays for every capability. Or text a rule must have on every task sits only in a case row, so the agent lacks it until it follows the row.
- One description, one install case or one folder's table covers a job outside the set. The agent loads this method for that job, and the capability it needs is under another method.

## What it is composed of

The author writes no file for the nesting. The author writes one exposure method, and the capability files its rows name. Read the page "Capability"¹ for the file and the folder. Read the page "Exposure method"² for which files expose content.

The one method is an entry point, whichever of the four it is. The page "Entry point"³ says how the body and the table are written. The page "Folder instructions"⁴ keeps what is its own when the method is folder instructions. The page "Routing table"⁵ has the table. The rows name capabilities. A row names the file that has the instructions. It does not name an exposure method.

The kind of exposure method is decided with the page "Choosing what to build"⁶. The steps say what nesting adds to that decision, for a skill, for a command, for a rule and for folder instructions.

## How to build it

1. **The extra descriptions, then what one method decides.** Find a task where the agent met a separate skill, rule, command or folder-instructions file for each capability, and the right first choice was the set. The reader opened one capability's method and did not have a document the others name. Or the reader had to choose among several descriptions for one purpose before any work. That miss is the failure. The cause is plain exposure: one exposure method for each capability. The situation is the agent choosing a skill to open, a rule to install or a command to invoke, or working in a folder whose instructions name one capability. Write what the one method decides: the set of capabilities, and that each capability is not its own exposure method. An author who writes one skill per capability, and then a parent that names those skills, has exposed exposure methods.

2. **Nest a shared purpose or the same documents. Do not nest a refusal the reader must match before any load.** Nest when you can point to one purpose sentence that covers these capabilities and does not cover a neighbor's job, or to one document that two or more of them name. That document is not in the list the agent already has, so the agent cannot choose it there. Do not nest when each capability would need its own description that names the other as the load to refuse, and the reader can match that sentence before either load. That sentence has to be read before any load of the set.

   Weak: "Expose the questioning capability and the defining capability through one skill."

   Strong: "Expose each through its own skill. Each description names the other as the load to refuse."

   The weak line hides a refusal the reader can match before either load.

3. **Take the cost of one method to the kind decision.** Decide the kind with the page "Choosing what to build"⁶. The one method will name every capability in the set. That is what nesting adds.

   When the kind is a skill, the agent has one description before it chooses a capability. Read the page "Skill"⁷ for that load. The description has to cover every capability's job, as the page "Entry point"³ says. Do not also write a skill for one capability of the set. Each extra skill is another description.

   When the kind is a command, the human invokes one name for the set. Read the page "Command"⁸ for that invoke. The word that picks the capability is typed with that name, as the page "Entry point"³ says. The capabilities are not commands. The human will not invoke a second name to pick one.

   When the kind is a rule, the table is in the body, so it is on every task. Read the page "Rule"⁹ for that copy. A rule is the kind only when that cost is the standing instruction. Text the agent must have on every task stays in the body, or in a row that says to read it on every reading. It does not sit only in a case row. A capability the agent needs only when a point comes is a row, not a paste of its text into the body.

   When the kind is folder instructions, the harness reads the file whenever the agent works in the folder. That file is an entry point. Read the page "Folder instructions"⁴ for what is its own. Write the body and the table as the page "Entry point"³ says. A capability only one kind of work in that folder needs is a row, not a line of the body. Do not write a skill for that capability when the work is only in this folder.

4. **Write each capability as a capability, and write one exposure method for the set.** Write the file as the page "Capability"¹ says. Do not also put that text in `skills/`, `rules/` or `commands/`. The rbtv CLI installs a file in those folders, and it does not install a page in the capabilities folder. The one exposure method is the only one for the set.

   Weak: "Write a skill for design tokens and a skill for the visual check, and a third skill that names both skills."

   Strong: "Write one skill. Its rows name the token capability and the check capability."

   The weak line exposes two exposure methods inside a third. The rbtv CLI accepts all three.

5. **Name the capability file, not another exposure method.** Write the table as the page "Routing table"⁵ says. A row names the capability that has the instructions. It does not name a skill, a rule, a command or folder instructions. It does not name a file that only lists other files. Write the file cell as the page "Entry point"³ says. When the method is folder instructions, take the link from the page "Folder instructions"⁴.

   Weak: `| office |`

   Strong: `| [Design tokens](../capabilities/design-tokens.md) |`

   The weak line names an exposure method. The strong line names the capability.

6. **Split a set that one method cannot cover.** When one description, one install case or one folder's table cannot cover every capability without also matching a job outside the set, write two exposure methods. Each nests its own capabilities. Decide each kind with the page "Choosing what to build"⁶. Neither row names the other method.

   Weak: "Keep one skill, and have its row name the office skill."

   Strong: "Write two skills. Neither row names the other."

   The weak line puts an exposure method inside an exposure method. The strong line splits the set.

- When you edit: a new file in `skills/`, `rules/` or `commands/` is a new exposure method as soon as it is installed. Ask step 2 again in the same change. The rbtv CLI does not ask whether one method already exposes that content.
- When you convert: an outside skill folder whose extra files are several capabilities becomes one exposure method and those capabilities, not one skill per file. A set of outside commands that share a purpose becomes one command, and the others become capabilities. When a part is another kind of thing in rbtv, decide it with the page "Choosing what to build"⁶.
- When you review: list every skill, rule, command and folder-instructions file the agent would meet, and mark the capabilities that share a purpose or the same documents. A review that only reads the one method misses a capability that still has its own exposure method.

Checks:

- A reviewer sees one exposure method for the set, and no skill, rule or command whose text is one capability of that set. The rows name capability files. No row names an exposure method. A rule does not leave text every task needs only in a case row. Folder instructions do not paste a capability that only one kind of work needs into the body.
- The rbtv CLI accepts the exposure method. Acceptance does not show that the capabilities lack their own exposure methods. A capability page is not installed, so acceptance of the method does not show that the rows open.
- Give the agent the one method, and not a separate method for each capability, with one task for each capability. The agent loads the one method and opens the capability the row names. Then add a separate skill for one capability and give that task again. If the agent loads that skill and skips the one method, the nesting was not done.

## References

| # | Page | File | Read | When | To |
|---|---|---|---|---|---|
| 1 | Capability | [Capability](glossary/capability.md) | must | | write each capability, and take that the rbtv CLI does not install it |
| 2 | Exposure method | [Exposure method](glossary/exposure-method.md) | when | deciding what exposes the content | take that a skill, a command, a rule and folder instructions are the exposure methods, and an agent is not |
| 3 | Entry point | [Entry point](glossary/entry-point.md) | when | writing the one method, whichever of the four it is | write the body and the table, and take that the same four things are entry points |
| 4 | Folder instructions | [Folder instructions](glossary/folder-instructions.md) | when | the one method is folder instructions | write that file and its table, and take that the harness reads it on every visit |
| 5 | Routing table | [Routing table](glossary/routing-table.md) | when | writing the rows | write the table, one column for each part |
| 6 | Choosing what to build | [Choosing what to build](choosing-what-to-build.md) | when | deciding the kind of the one method, or a converted part is another kind of thing in rbtv | decide the kind, with the cost this page names |
| 7 | Skill | [Skill](glossary/skill.md) | when | the one method is a skill | take the load: the agent has the description before the table |
| 8 | Command | [Command](glossary/command.md) | when | the one method is a command | take the invoke: the human types the name before the table |
| 9 | Rule | [Rule](glossary/rule.md) | when | the one method is a rule | take the copy, and that the body is on every task |
