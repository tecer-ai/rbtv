# Writing a capability

Writing a capability is how you write the page an agent reads after a route, when that page carries a method or knowledge. That page is not a glossary entry, and it is not a principle, a template or a schema. The page "Capability"¹ says what a capability is, and how the instructions are written from what the route passed. That page also names the layout of a glossary entry, a principle, a template and a schema, and says that a tool's CLI under `capabilities/tools/` is not written as a capability. The page "Writing a glossary entry"² has the list of decisions, the three tests, the weak line and the strong line, the form of a reference, and the wording. Follow that page for those. On this page, "you" write the file. "The agent" arrives by the route and does the work.

Outside rbtv, extra files sit in a skill's own folder, and the skill package carries them. Public guidance gives such a file no required sections. It recommends examples of inputs and outputs, and it asks the author to move detail out of the skill so the skill stays short. Here the file is not in the skill folder, and a whole example is not a part. Read this page when the file is a method or knowledge, and not one of those four. Write the file so that the agent does the work that remained. The agent has nothing but the file, the pages that the file names, and the facts that the route passed.

## How it fails

The page "Capability"¹ says the rbtv CLI does not read the file. Headings do not keep the work from failing.

- The file has the parts of a glossary entry: a definition of a term, a section that names parts the agent does not write, and a template of the file itself. The agent reads a definition and copies a layout. The work that remained is not those parts.
- The steps follow the order in which you found the decisions, or they repeat the page "Writing a glossary entry"² with this work's name put in. The agent researches, or it writes a page. The decision the route left open is missing.
- The file was never tried on a task that the route names. The remaining work is untested, so a later agent meets a failure that acceptance of the component did not show.
- Facts are numbered as steps, or the decisions are written as facts only. The agent follows an order that is not the work, or it has the facts and no next action.

## How to do it

1. **Keep the parts that apply.** When the file is a glossary entry, or when it is a principle, a template or a schema, write the layout the page "Capability"¹ names, and stop. This page is for the other file. Use these parts, in this order. Leave out a part that the work does not use. Write no heading for a part you leave out, and do not add a line that announces the omission.

   | Part | Heading | Absent when |
   |---|---|---|
   | What the work is, and what it is for | none: the lines under the title | never |
   | The failures of the work | `## How it fails` | never |
   | The files the agent writes | `## What it is composed of` | the agent writes no file, and decides no part of a file |
   | The steps | `## How to do it` | every sentence is a fact, and no sentence is a decision the agent makes |
   | The layout of one file that the work produces | `## Template` | the work does not produce one file of a fixed layout |
   | The pages the file names | `## References` | the file names no other page |

   The lines under the title are written as the page "Capability"¹ says for the facts that the route passed. They are not a definition of a term. Otherwise use `## How to do it`. Do not invent a further heading. Those two are the only step headings.

   A `## Template` section shows one file that the work produces. It does not show the shape of the capability file. That shape is the lines of the file, and the page "Capability"¹ has it. A writer who finds a template copies the template into the file that the agent produces.

   Weak: "Under the title, define the term. Add How it fails, what it is composed of, how to build it and a template, because a glossary entry has those parts."

   Strong: "Under the title, state the work and what it is for. Add How it fails and How to do it, and leave the template out, because this work produces no file of a fixed layout."

   The weak line copies a glossary entry's headings, so the agent reads a template of this file and does not do the work.

2. **Find each step from a decision the route leaves open.** Follow the page "Writing a glossary entry"² for the list of decisions and for the three tests. Ask which decision the route leaves open and the nearest capability does not. Each such decision becomes one step, in the order the agent meets it. Keep the list out of the file. Write each step as an order. Put the reason in the step, or in the sentence after the step. The reason is the fact that makes this decision and not another. A sentence that stays true when the nearest capability's subject replaces this work belongs on the page "Capability"¹ or on the page "Writing a glossary entry"². Name that page at the step. Do not write the sentence again.

   A step is a decision the agent makes. A fact the agent uses is not a step. When every sentence is a fact, write no steps heading. Outside guidance recommends steps and examples in a skill body. A fact in this file is still not a decision, so do not number it to match that guidance.

   Weak: "The route passed both reports and not the lines that disagree. First list the failures you found, then name those lines. When only one report was passed, stop and name the missing report."

   Strong: "The route passed both reports and not the lines that disagree. The first step names those lines. When only one report was passed, stop and name the missing report."

   The weak line puts your research first, so the agent lists failures and does not name the lines.

3. **Test with an agent that a route sent.** Give an agent the file, every page that the file names, and only the facts that the route passed. Phrase the job as the person would phrase the task that the route names. Withhold the file until the route names it. A run passes when the remaining work is done, none of the failures you listed appears in the result, and no weak line or strong line was copied. Then give a task from another route that also names the file. When editing, converting or reviewing goes wrong in a way the other work does not, give a task for that mode. The page "Writing a glossary entry"² says when such a mode needs its own instruction. Do not launch create, convert and review twice each. The rbtv CLI does not install this file, so no run of the rbtv CLI accepts or refuses it.

   Weak: "Treat the file as done when the component is accepted, before that agent finishes the remaining work."

   Strong: "Treat the file as done only after that agent finishes the remaining work on the facts that the route passed. Acceptance of the component is not this result."

   The weak line stops before the agent does the work. The page "Capability"¹ says what acceptance shows.

When you edit the file, change it in the source, and ask step 1 again if the edit adds a part that the work does not have. The page "Capability"¹ says where that edit is seen, and when the route's row has to change with the file.

When you convert an outside file kept next to a skill, write the file here when some route has to point the agent at it. The page "Capability"¹ says how that continuation is written. Drop an example of inputs and outputs. The page "Writing a glossary entry"² says not to show a whole instance. Do not cut a reason to meet a length from the outside guidance. The agent then lacks the reason on a case that the step does not name. When the outside file also contains a skill, a rule or a command, the page "Writing a glossary entry"² names the page that decides that part.

When you review, start from the step that named the file, and use only the facts that the step passed. Matching headings to a glossary entry is not a review. Ending at acceptance of the component is not a review.

Checks:

- The file has only the parts that apply. The lines under the title are not a definition of a term. A template section exists only when the work produces one file of a fixed layout. There is no steps heading when every sentence is a fact.
- No step stays true of the nearest capability. A search of the file finds no sentence of eight or more words copied from the page "Writing a glossary entry"², from the page "Capability"¹, or from the nearest capability.
- The steps are decisions the agent makes, in the order the agent meets them.
- The agent has the file, the pages that the file names, and only the facts that the route passed. It does the remaining work on a task that the route names, and on a task that another route would name. No weak line or strong line was copied. Acceptance of the component is not that test.

## References

| # | Page | File | Read | When | To |
|---|---|---|---|---|---|
| 1 | Capability | [Capability](glossary/capability.md) | must | | take what a capability is, how the instructions are written from what the route passed, the layout for a glossary entry and for a principle, a template or a schema, and that the rbtv CLI does not read the file |
| 2 | Writing a glossary entry | [Writing a glossary entry](writing-a-glossary-entry.md) | must | | take the list of decisions, the three tests, the weak line and the strong line, the form of a reference, and the wording |
