# Harness

A harness is the application that runs the model and injects scaffolding into the agent's context. It is not the model, and it is not the scaffolding. Outside rbtv a harness is whatever application runs an agent, and each application reads its own folders. In rbtv the harnesses are Claude Code, Codex and OpenCode, and no other. The page "Agent"¹ says an agent is a model, a harness and scaffolding.

The harness is what puts a rule, folder instructions and a skill's description in front of the agent, and on one of the three a file of that kind may have no equivalent. An author wants the word when a sentence names what an agent receives, or when a file written for one of the three must still be true on another. Name the harness that injects the text. Do not treat what one harness injects as what the other two inject.

Claude Code injects a rule from its rules folder. It loads a file with no path list at the start of a session. It strips the frontmatter before the model sees the file. The only frontmatter field it reads is a path list. A rule in rbtv does not carry one. Codex has no rules folder of this kind. It uses the word rule for a permission on a command, and that permission does not put text into the agent's context. OpenCode reads no rules folder. Its rules are the instructions file it already loads. The page "Rule"² says what each harness then receives, and how to write the body.

Each harness injects one instructions file for a folder. Claude Code's name for that file is `CLAUDE.md`. Codex and OpenCode's name for that file is `AGENTS.md`. Claude Code, with its default setting for project instructions, reads `AGENTS.md` only when the working directory and the directories above it have none of `CLAUDE.md`, `.claude/CLAUDE.md` and `CLAUDE.local.md`. OpenCode reads `CLAUDE.md` only when that folder has no `AGENTS.md`. Codex reads the instructions files from the project root down to the working directory at the start of a run, and stops when their combined size reaches its limit. A body past the limit in force is still cut, because the rbtv CLI does not remove the limit. The page "rbtv CLI"³ says what the rbtv CLI writes for the limit and for the other file name. The page "Folder instructions"⁴ says which file the author writes, and what differs for a subfolder, an import and a comment.

Each of the three shows a skill's name and description, and loads the instructions when the agent chooses the skill. Claude Code also lets a person type the skill's name. A typed name is not how rbtv opens a skill. The page "Exposure method"⁵ says who decides. Claude Code cuts the skill listing. Codex may shorten a description in the list that it shows first, and may leave a skill out of that list when many are installed. The page "Entry point"⁶ says where to put the boundary so a cut still leaves it. The page "Skill"⁷ says what that description contains.

Codex's listed command file carries no description. Claude Code and OpenCode's listed command files carry one. The page "Command"⁸ says what the human then chooses from. Claude Code and Codex run a hook from a settings file. OpenCode has no settings file for a hook. Its extension is a JavaScript plugin. The page "rbtv CLI" says what a pass shows when that harness has no hook file. The page "Choosing what to build"⁹ says what to do when the action must also happen under OpenCode. The page "Cognitive unit"¹⁰ says not to name one harness's tool as the only way to do a step.

A harness recognizes a sub-agent from a file of its own. The page "Agent" says that placement and the placement as an rbtv agent. The installation record names the harnesses that the installation receives, as the list `harnesses` in `.rbtv/config/install.json`. The values are `claude`, `codex` and `opencode`. An rbtv agent's record names the one harness that runs that agent, as `harness` in `agent.json`, and only in an installation. The page "Agent" says a folder a component ships names no harness there. The page "rbtv CLI" says what the rbtv CLI writes into those two records.

The harness injects the installed rule. The model does not. A misuse is "The harness is the prompt the agent follows."

## References

| # | Page | File | Read | When | To |
|---|---|---|---|---|---|
| 1 | Agent | [Agent](agent.md) | when | a sentence is about to treat the scaffolding or the model as a harness, or a component record is about to name a harness | take that an agent is a model, a harness and scaffolding, and that a folder a component ships names no harness |
| 2 | Rule | [Rule](rule.md) | when | the text is a rule, or a condition sits in frontmatter | take what each harness receives, and write the body so the condition is in it |
| 3 | rbtv CLI | [rbtv CLI](rbtv-cli.md) | when | the question is what the rbtv CLI writes for a harness, or what a pass shows | take the files it writes, the limit it raises, and what a pass does not show |
| 4 | Folder instructions | [Folder instructions](folder-instructions.md) | when | the file is the one a harness reads for a folder | take which file the author writes, and what differs for a subfolder, an import and a comment |
| 5 | Exposure method | [Exposure method](exposure-method.md) | when | the question is who decides that a skill, a command, a rule or folder instructions arrives | take who decides, and that a person who types a name uses a command |
| 6 | Entry point | [Entry point](entry-point.md) | when | a skill description may be cut or shortened in the listing | take where to put the boundary so a cut still leaves it |
| 7 | Skill | [Skill](skill.md) | when | the file is a skill | take what the description contains, and that the harness lists a pointer |
| 8 | Command | [Command](command.md) | when | the file is a command, or the human chooses from a description | take what the listed file carries on each harness, and what a name the harness already lists does |
| 9 | Choosing what to build | [Choosing what to build](../choosing-what-to-build.md) | when | an action must run even if the agent ignores every text, and OpenCode is among the harnesses | decide the kind |
| 10 | Cognitive unit | [Cognitive unit](cognitive-unit.md) | when | a step names a tool | take that the step does not name one harness's tool as the only way |
