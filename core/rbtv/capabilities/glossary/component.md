# Component

A component is the folder inside a module that groups the files of one subject, at `<module>/<component>/`, with the record `<component>.json`. Outside rbtv a component is often a package or a piece of a screen. In rbtv the rbtv CLI finds the folder by that record, and the folder a file sits in decides how the file is exposed. The page "Module"¹ says what the parent folder is.

A component gives one subject a home, and a later author judges from the first sentence of the description whether the next file belongs in it. An author wants one when the page "Choosing where to build"² has given the work its own folder. Write a component so that every file in it is covered by that sentence, and each file sits in the folder the rbtv CLI scans for its kind.

## How it fails

The rbtv CLI can accept this folder, and a file of another subject can still sit beside a file the first sentence covers. It reads the record and the folders it scans. It does not compare that sentence with the files.

- The first sentence names the files already inside. It does not name the closest work a later author might add by mistake, or it names that work only after the first period. The page "Choosing where to build"² says what a list then shows. The next author puts other work in.
- A file of the subject sits in `references/`, `prompts/`, `workflows/` or `tools/` at the component root. A list of the component does not show that file. The next author writes a second copy in a folder the rbtv CLI scans.
- The component organises work in folders, and the shape of those folders is stated only in a skill. The next folder of that work follows the skill, and a second skill cannot share the statement.
- An index file lists the pages of a folder. The later agent reads the list and does not open the page that has the instructions. The page "Progressive disclosure"³ says why that list fails.
- The folder name is a gerund, or it contains a capital letter. The id is that name. A later author reads the id as an action, or cannot match it to the lower-case names beside it.
- Rules for editing this component sit in `folder-instructions/`, or instructions meant for another folder sit only in this component's own instruction file. The first reaches an installation that selects that folder-instructions file. The second stays in the repository.
- A standing decision is narrated in a page, or `decisions.md` keeps the old decision beside the new one. The later agent follows the narration, or follows the old decision.

## What it is composed of

Write the folder `<module>/<component>/`. It always has the record `<component>.json`, named after the folder. The page "`<component>.json`"⁴ says how that file is written. This page does not list its fields. The description in the record is the boundary. The page "Choosing where to build"² decides whether the folder is in the repository or in the mirror.

Write each kind in its folder, as its page says. The page "rbtv CLI"¹⁹ says which folders the rbtv CLI scans.

- `skills/` has the skills, one file each, as the page "Skill"⁵ says.
- `rules/` has the rules, one file each, as the page "Rule"⁶ says.
- `commands/` has the commands, one file each, as the page "Command"⁷ says.
- `agents/<name>/` is the folder of one agent, as the page "Agent"⁸ says. An agent is that folder, with `agent.md` and `agent.json`.
- `hooks/` has the hooks, one file each, as the page "Hook"⁹ says.
- `mcp-servers/` has the MCP servers, one file each, as the page "MCP server"¹⁰ says.
- `packs/` has the packs, one file each, as the page "Pack"¹¹ says.
- `folder-instructions/` has the sections that the rbtv CLI writes into other folders, one file each, as the page "Folder instructions"¹² says.
- `capabilities/` has the capabilities, the principles and the glossary, as the page "Capability"¹³ says. The rbtv CLI does not install a page there. A route reads it in the source.
- `capabilities/tools/<tool>/` is the folder of one tool, as the page "Tool"¹⁴ says. Its record is the one file under `capabilities/` that the rbtv CLI reads as a record; it also reads the first line of the tool's CLI that the record names.

The glossary is `capabilities/glossary/`. It contains the entries of this component's own terms, and the folder artifacts of work this component organises. The page "Writing a glossary entry"¹⁵ says how an entry is written. The page "Terminology is king"¹⁶ says that an rbtv term stays in the rbtv glossary. The page "Folder artifact"¹⁷ says what that entry states. A component has no index file. Do not write `capabilities.md`, `principles.md` or `glossary.md`.

When a standing decision of this component exists, write `decisions.md` at the component root. The rbtv CLI does not read it. Do not write the file when no standing decision exists. Read the page "Keep it stupidly simple"¹⁸ before you add a file no stated need requires.

A file the harness reads when an agent works in the component folder is folder instructions for that folder, as the page "Folder instructions"¹² says. It is not a file in `folder-instructions/`.

Read the page "rbtv CLI"¹⁹ for a refusal in this folder, and for what a pass shows. Do not repeat a refusal here.

## How to build it

1. **The file a later author will misplace, then the boundary.** Find the work this folder is for. The page "Choosing where to build"² has already given that work its own component. The failure is a file of this subject left out, or other work sitting in this folder. The cause, for a component, is the first sentence. It names the files already chosen. It does not name the closest work a later author might add by mistake. The situation is before the first file is written, and again when a file is added. Write the boundary from that failure. The next file of this subject goes in. Other work stays out.

2. **Name the folder with a noun, in lower case, with hyphens.** The id is the folder name. The rbtv CLI stores that name and does not check it. A gerund is stored and reads as an action. A capital letter is stored and is the id a list shows. Use a noun a later author can tell from the names beside it. The page "Terminology is king"¹⁶ says how to check the name against the glossary.

   Weak: "Name the folder planning."

   Strong: "Name the folder notes."

   The weak line is a gerund. A later author reads the id as an action.

3. **Write that boundary as the first sentence of the description.** Write the record by the page "`<component>.json`"⁴, in the same change as the folder. The rbtv CLI finds the component by that file. Name, in that first sentence, the work that belongs and the closest work that must stay out. The page "Choosing where to build"² says what a list shows of that sentence, so words after the first period are missing from the line. The description is plain sentences, not the row of a routing table that the page "Routing table"²⁰ gives a skill, a rule, a command or an agent: the reader of this sentence is placing a file, not choosing a load. The page "Single source of truth"²¹ refuses a second copy of the boundary in another file. Apply the page "Scaffolding language"²² to that sentence.

   Weak: "Notes a person keeps. Not a meeting summary."

   Strong: "Notes a person keeps, not a meeting summary and not mail."

   The weak line ends the belonging at a period. A list without `--full` stops at that period, and the exclusion is not shown.

4. **Put each file in the folder the rbtv CLI scans for its kind.** A skill goes in `skills/`, and the same for each folder in the list above. A page a route reads, and that the rbtv CLI does not install, goes under `capabilities/`. A tool goes under `capabilities/tools/`, as the page "Tool"¹⁴ says. Do not put the work in `references/`, `prompts/`, `workflows/` or `tools/` at the component root. Those folders are not scanned. Rules for editing this component stay in the instruction file of this folder, as the page "Folder instructions"¹² says. Instructions for another folder go in `folder-instructions/`.

   Weak: "Put the framework in references/, beside the record."

   Strong: "Put the framework under capabilities/, and name that file from the skill that uses it."

   The weak line puts the file in a folder that no route names and the rbtv CLI does not scan, so the next author writes a second copy.

5. **Put this component's own terms, and its folder artifacts, in `capabilities/glossary/`.** A word that names a subject of this component, and is not an rbtv term, has its entry here, as the page "Terminology is king"¹⁶ says. The page "Writing a glossary entry"¹⁵ is how that entry is written. Write it together with the first file that uses the word. When the component organises work in folders, state each folder artifact as an entry in this glossary, as the page "Folder artifact"¹⁷ says. Do not state that shape only in a skill. Do not write `glossary.md`.

   Weak: "The skill lists which files a work folder contains."

   Strong: "The glossary of this component states which files a work folder contains, and the skill names that entry."

   The weak line makes the next work folder follow the skill, and a second skill cannot share the statement.

6. **Write `decisions.md` when a standing decision would otherwise sit in a page.** Put it at the component root. A page of the component describes the design as it is; a comparison with an earlier design goes in that file, and a superseded decision is replaced, not appended. Do not write the file when no standing decision exists.

   Weak: "The page says this skill replaces the older notes skill, which lived in office."

   Strong: "The page says what the skill does. The move from office is a line in decisions.md, and the older line is replaced."

   The weak line puts the comparison in the page a later agent follows.

7. **Keep every later file inside the first sentence.** Before you add a file, read the first sentence. When the sentence does not cover the file, the file does not go in this component. Decide the other home with the page "Choosing where to build"². The page "Choosing what to build"²³ settles the kind, and the page "Choosing where to build"² says that a second kind of file is not a second subject. When the subject of the component changes, change the first sentence in the same change.

When you edit a file that already has this home, do not move the component. Follow step 7 when the subject changes. When the folder name changes, change the record's file name in the same change, and the rest of the rename as the page "Terminology is king"¹⁶ says.

When you convert, do not take the outside folder's name as this folder's name. Place each file in the folder the rbtv CLI scans for its kind. A page that a route must name goes under `capabilities/`. An outside `package.json` is not the record. Write `<component>.json` by the page "`<component>.json`"⁴. Send a part that is not a file of this component to the page "Choosing what to build"²³. Place a file that belongs to one installation as the page "Choosing where to build"² says.

When you review, quote the first sentence and name one file it does not cover, or say that every file is covered. Then name any file outside the scanned folders, any index file, and any work-folder shape that is stated only in a skill. A review that only checks that the record exists misses a file the rbtv CLI did not list.

Checks:

- A reviewer sees a folder name that is a noun, in lower case, with hyphens. The first sentence names the work that belongs and the closest work that must stay out. Every file sits in a folder the rbtv CLI scans for its kind, or under `capabilities/`. This component's own terms, and any folder artifact the component organises, have an entry in `capabilities/glossary/`. No index file is present. `decisions.md` is present only when a standing decision exists, and no page narrates that decision. Rules for editing this component are not in `folder-instructions/`.
- The rbtv CLI accepts the record. That pass shows the record was found and each scanned file matched its kind. It does not show that the first sentence covers the files. It does not show that a file outside those folders is missing.
- Add one further file, using only the first sentence. Add it when that sentence covers it. Leave it out when that sentence excludes it. Then have the rbtv CLI list the component, as the page "rbtv CLI"¹⁹ says. A file outside the scanned folders is not in that list.

## References

| # | Page | File | Read | When | To |
|---|---|---|---|---|---|
| 1 | Module | [Module](module.md) | when | naming the parent folder | take what a module is |
| 2 | Choosing where to build | [Choosing where to build](../choosing-where-to-build.md) | when | the home is not yet this folder, the first sentence is written, or a later file may belong elsewhere | take the placement, the mirror, and how a list shows the first sentence |
| 3 | Progressive disclosure | [Progressive disclosure](../principles/progressive-disclosure.md) | when | about to write a file that only lists a folder | take why that list fails |
| 4 | `<component>.json` | [`<component>.json`](component-json.md) | when | writing the record | write the record, and do not list its fields here |
| 5 | Skill | [Skill](skill.md) | when | the file is a skill | take what `skills/` is for |
| 6 | Rule | [Rule](rule.md) | when | the file is a rule | take what `rules/` is for |
| 7 | Command | [Command](command.md) | when | the file is a command | take what `commands/` is for |
| 8 | Agent | [Agent](agent.md) | when | the file is an agent | take that an agent is the folder `agents/<name>/` |
| 9 | Hook | [Hook](hook.md) | when | the file is a hook | take what `hooks/` is for |
| 10 | MCP server | [MCP server](mcp-server.md) | when | the file is an MCP server | take what `mcp-servers/` is for |
| 11 | Pack | [Pack](pack.md) | when | the file is a pack | take what `packs/` is for |
| 12 | Folder instructions | [Folder instructions](folder-instructions.md) | when | writing the instruction file of this folder, or a file in `folder-instructions/` | take which of the two files to write |
| 13 | Capability | [Capability](capability.md) | when | the file is a page under `capabilities/` and is not a tool | take that the rbtv CLI does not install the page, and a route opens it in the source |
| 14 | Tool | [Tool](tool.md) | when | the file is a tool | take that the rbtv CLI reads `capabilities/tools/<tool>/` |
| 15 | Writing a glossary entry | [Writing a glossary entry](../writing-a-glossary-entry.md) | when | writing an entry in this component's glossary | write that entry |
| 16 | Terminology is king | [Terminology is king](../principles/terminology-is-king.md) | when | naming the folder, or placing a term | take that a glossary word keeps its meaning, and that an rbtv term stays in the rbtv glossary |
| 17 | Folder artifact | [Folder artifact](folder-artifact.md) | when | the component organises work in folders | state each folder artifact in this glossary |
| 18 | Keep it stupidly simple | [Keep it stupidly simple](../principles/keep-it-stupidly-simple.md) | when | about to add `decisions.md` or a folder no stated need requires | take that a file nobody needs is refused |
| 19 | rbtv CLI | [rbtv CLI](rbtv-cli.md) | when | the rbtv CLI should accept the folder, a refusal appears, or the component is listed | take a refusal, what a pass shows, and how to list |
| 20 | Routing table | [Routing table](routing-table.md) | when | about to write the description as a row with labels | take that this sentence is not that row |
| 21 | Single source of truth | [Single source of truth](../principles/single-source-of-truth.md) | when | a second file would also state the boundary | leave the description as the only statement of the boundary |
| 22 | Scaffolding language | [Scaffolding language](scaffolding-language.md) | when | writing the first sentence of the description | word that sentence |
| 23 | Choosing what to build | [Choosing what to build](../choosing-what-to-build.md) | when | the kind of a file is not yet settled, or a converted part is not a file of this component | settle the kind there |
