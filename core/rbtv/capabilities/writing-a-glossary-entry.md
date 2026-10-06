# Writing a glossary entry

A glossary entry is the one page that defines one term of rbtv. An agent reads it before it builds, edits, reviews or converts what the term names. The page says what the term means, what the thing is for, what it is composed of and how to build it, and it gives a template and the pages to read. Outside rbtv a glossary entry is a definition that a reader looks up. Here it is also the instructions that the builder follows. Each component⁵ keeps the entries of its own terms in its glossary.

An entry is for an agent that is about to build the thing and has never built a good one. An author writes an entry when rbtv gets a term, and corrects it in the same change as the file that the entry describes. Write an entry so that an agent builds a thing that does its job, with nothing but the entry and the pages that the entry links. Judge an entry by what an agent builds from it, never by how it reads.

Follow this page before you write, change or review an entry. On this page, "you" are the agent that writes the entry, and "the builder" is the agent that reads the entry in order to build. "The thing" is what the term names. An entry never says "the thing": it uses the term.

## How it fails

An entry can have every part and still fail the agent that builds from it:

- It lists parts and steps. The builder produces the usual version of the thing: the rbtv CLI accepts it, it has every part, and it does not do what the thing is for.
- Its steps could have been written without knowing the thing. They say what is true of writing any text for an agent, with the term put in. The builder learns nothing about what is hard in this one thing, and makes the mistakes that only this thing has.
- Its words are not the words that a reader expects. The builder reads a sentence twice, or takes a word in its usual sense and acts on the wrong meaning.

## What an entry is composed of

One file, named after the term in lower case with hyphens, with these parts in this order. A part that does not apply is absent: no heading and no "not applicable".

| Part | Heading | Absent when |
|---|---|---|
| The meaning, then the purpose | none: they follow the title | never |
| The failures | `## How it fails` | the term is a word only |
| What the thing is composed of | `## What it is composed of` | the thing has no part that an author decides about |
| How to build it, ending with its checks | `## How to build it`; `## How to work with it` when a CLI writes the thing; `## How to apply it` for a standard | the term is a word only |
| The template | `## Template` | the thing is not one file that an author writes |
| The table of references | `## References` | the entry names no other page |

An entry has no part that shows a whole instance. A whole example never shows every case, and a builder copies it. Where one point of a step is often done wrong, the step shows that point twice, as one weak line and one strong line. The template shows the layout.

The parts, their order and the titles of the steps may be the same in every entry. What is written under them may not: the section "Steps written from the thing" says how to tell.

The kind of term decides the parts and the test:

| The term names | Parts between the first part and the references | The test of step 6 |
|---|---|---|
| a file or a folder that an author writes and that the rbtv command⁷ adds: a skill, a rule, a command, an agent, a hook, an MCP server, a tool, a pack, folder instructions, a self-contained skill | composed of, how to build it, template when the thing is one file | create, convert, review: twice each |
| a record with fixed fields | composed of, how to build it or how to work with it, template or the linked schema⁶ | one create task |
| a cognitive unit that has sections, such as a prompt | composed of, how to build it with one part for each section, template | one create task |
| a folder | composed of; how to build it only when an agent decides what goes into the folder | one create task: place three files |
| a file that a CLI writes | composed of, how to work with it | one task: change what the file shows |
| what several kinds of thing have in common, such as a cognitive unit | composed of, how to build it with the steps that every one of those kinds shares | one create task, with the entry of one of those kinds |
| a standard that an author applies to a text | how to apply it | one task: apply it to a text that breaks it |
| a principle | how it fails; how to apply it, as steps or cases with weak and strong lines, ending with its checks. Its first paragraphs state the principle in a plain sentence, without the form "even over", and say what it is for | one task: a design that breaks the principle in two ways, to correct |
| a capability: a page with a method or with knowledge that an exposure method or a step of a prompt sends the agent to | how it fails; how to do it, as steps with weak and strong lines, ending with its checks; a template only when the work produces one file of a fixed layout. The page "Writing a capability" says what differs from an entry | one task that arrives by the route, and one by a second route |
| a word only: nothing that anyone writes, runs or stores | none: the first part ends with one sentence that uses the word and one that misuses it | a sorting task |

A thing that an author and a CLI both write gets the parts of its kind for the author's share. The CLI's share goes under "How to work with it".

## Which entry owns what

Two things overlap when most of the work on one is also the work on the other: an agent and its prompt, a task and its scope, a skill and the capabilities that it routes to. Without a rule, their entries say the same thing twice, and the two copies stop agreeing at the first edit. Before you write, list the entries that overlap with yours: of the thing that contains yours, of the things that yours contains, and of the things with the same form. Then give each fact, each step and each check to one entry.

1. **A thing that is never built alone is a section, not a term.** Ask whether a builder is ever asked to create, edit or review it apart from the thing that contains it. When the answer is no, as for the role of a prompt, write no entry for it. The entry of the containing thing gives it a part inside "How to build it", under the name of the section, in one fixed shape: what the section is for and the failure that it prevents; when the thing has it; how to write it; one weak line and one strong line; its checks. Write once, outside those parts, what is true of every section.

2. **A thing that is built alone has its own entry, and the entry of the thing that contains it does not teach it.** A prompt is improved without a change to the folder of its agent, so it has an entry. The agent entry says three things about the prompt: that it is there and what it does for the agent, in one line; what has to agree between the two, such as the name; and where to read how it is built, as a `must` reference. It gives no instruction on writing the prompt and repeats none of its checks.

3. **A step that two entries need is written once, in the entry of the thing that the step produces.** Naming the failure and the purpose of an agent's work produces the prompt, so the prompt entry has that step. The agent entry keeps only the failure that is its own, such as why a separate agent is needed, and sends the builder to the prompt entry for the rest.

4. **What several things have in common has one page.** The description of a skill, of a rule, of a command and of an agent is one row of a routing table. The page "Routing table"⁴ has the form, and each of the four entries says only what each part of the row contains for its thing. The same is true of an instruction. A skill, a rule, a command and a prompt are all cognitive units, and what is true of writing every one of them is written once, in the page "Cognitive unit"²: write the text that does the work before the description, open it with the purpose, say what the agent does when an input is missing, name the tool for an exact answer, give a finding as the passage, its effect and the repair. An entry references that page and keeps only what its thing adds or does differently. The shared page has only what is true of every one of those kinds, and nothing of one kind.

   The entry of a kind opens "How to build it" with one sentence that tells the builder to follow the steps of the shared page. After that sentence it has only two kinds of step: a step that the shared page does not have, and a step of the shared page that this thing does differently. It gives no step the title of a shared step only in order to say "as the shared page says". An entry that has every step of the shared page again, each with one sentence added, is the shared page with a noun changed. Write no sentence about how the pages are divided, such as "do this in place of the first step of that page", and no sentence that announces what the entry adds, such as "what this file adds is the moment": say the thing itself.

5. **Each entry defines its own term, and names every other thing by its term.** The definition of an agent names the prompt and does not say what a prompt is.

To decide which entry owns a sentence, ask which file a writer has to change when the fact changes. That entry keeps the sentence, and every other entry references it. When one of two entries is left with almost nothing of its own, stop and report it to the owner: the thing may be a section of the other, or the two may be one term.

## Steps written from the thing

The steps of "How to build it" are the most critical part of an entry. They fail when they are this page's own sentences with the term put in: such steps are true, and the builder would have followed them without the entry.

Write the steps from one question, which you answer before any sentence of the entry: **what is hard about building this thing that is not hard about building the things nearest to it?** A command and a skill are both instructions in one file, with a name and a description. What is hard in a command is not hard in a skill: a human chooses the command from its name, before the agent has read a line of it, and types what the action needs together with the name. Those are the facts that the steps of the command entry are written from.

Answer the question as a list of decisions. For each decision, record three things:

- the fact about the thing that forces the decision, with the path and the line where you read it;
- what the author has to decide because of that fact;
- what the finished thing does wrong when the author decides badly, and why the rbtv CLI still accepts it.

Each decision of the list becomes one step, or the reason of one step, and none is left out to make the entry shorter. The list stays in your record. The entry does not have to describe where the thing sits in rbtv, and a sentence does not become specific because it names a folder. A step is specific when the builder decides something differently because of it.

Do not turn the way you worked into the builder's steps. You list failures and decisions in order to write the entry. The builder needs the decisions, in the order of its own work.

Three tests show a step that is not written from the thing. Apply them to the draft, with the entries of the two nearest terms open beside yours:

1. **The swap test.** Read each sentence with a neighbouring term in place of yours. When the sentence is still true, it is not about your thing. Then do one of three things. Add what is different for your thing. Or move the sentence to the page that rule 4 of "Which entry owns what" gives it, and reference that page. Or delete it. A step title may be the same in every entry. The sentences under it may not.
2. **The copy test.** Search your entry for each sentence of eight words or more that is also in this page, in its template or in one of the two nearest entries. Write each one again from your list of decisions, or reference the page that owns it.
3. **The three-sentence test.** Say in three sentences what a builder has to get right for this thing. When the three sentences could be about another term, the entry is not yet about yours.

## How to write one

Two requirements apply to every part. Meeting one does not meet the other.

- **The language is scaffolding language.** The goals and the tests of the page "Scaffolding language"¹ apply to every sentence. A shorter entry is never a goal.
- **The content is what the builder has to understand**: the purpose of the thing, what is hard about it, the reason of each instruction, and the criterion of each step that takes judgment. Write a point that is subjective as an order with its reason. Never leave it out because it is hard to word.

1. **Know the thing.** Gather the term, its current entry, every older page about it, the CLI that reads or writes it, the owner's decisions about it, and the entries that overlap with it. Read each statement about what a CLI, a harness or an agent does in the CLI's code, in its help output, in the schema or in the file itself, and record it with its path and line. Never take such a statement from a page alone.
   - When a page and the CLI disagree about what the CLI does today, the CLI is right, and you report the page.
   - When the CLI and a decision of the owner disagree, record both and report the gap. Do not teach as a fact what the CLI does not do yet, and do not teach what the owner has decided to remove.
   - When an older page and a decision of the owner disagree, the decision is right.
   - Record a fact that you cannot find as open, and never guess it: the builder cannot tell a guessed sentence from a checked one. An open fact goes into your report and never into the entry. Stop and report when it decides what the builder writes.
   - When the thing also exists outside rbtv, read the public guidance on building it. Keep from it what corrects a failure of step 2, and what rbtv does differently.
   - Agree with the user on what the entry has to do before you write it. The folder `meta/functions/skills`⁸ has functions for that, and when they are installed you must use them: `interview` when what the user expects is written in no decision and in no request, and `investignosis` when how the thing works today has to be found in the code or in the files. When no user can be reached, record each point that you would have asked, and report it with the entry.

2. **Find what goes wrong.** An entry is written against the failures of the thing, so find them before you write. Use three sources.
   - The real instances in the repository. Read each one as its reader meets it, and note where it fails at what the thing is for.
   - For a thing that the rbtv CLI adds, a first build with no guidance. Launch a fresh agent as the skill "Sub-agents"⁹ says. Give it a job for such a thing in two or three sentences, as a user would write them, and a folder to write into. Do not say what you expect. Its faults are the ones that a capable agent makes without an entry.
   - The warnings of the older pages and of the public guidance.

   Then list the failures. A failure is a decision of the author that makes the finished thing fail at what it is for, and that no CLI refuses. For each one, record the situation, the wrong decision, what it causes, and why the rbtv CLI accepts it. Faults with one cause are one failure. The list must have at least one failure that the nearest kinds of thing do not have. "The description is vague" is the failure of a skill, of a rule and of a command alike: say what is vague in this thing, for its reader. Close the list before you write the entry, because step 6 tests against it.

3. **Find what is hard about this thing.** Answer the question of "Steps written from the thing", as a list of decisions with their three records. Take the decisions from the facts of step 1 and from the failures of step 2. When you find none that the nearest things do not share, stop and report: either you do not know the thing yet, or it is not a term of its own.

4. **Write the entry**, part by part, into the template below.
   - **The meaning.** Define the term in a first sentence that can be read without the rest, because a reader sent from another entry often reads only that sentence. When the thing also exists outside rbtv, say where the version of rbtv differs, because the reader assumes the outside meaning.
   - **The purpose.** Say what the thing is for, in one or two sentences. Then say when an author wants one. End with one order that says what a well-built thing achieves: "Write a ... so that ...". Do not say which other kind of thing to build in place of this one. That decision is made with the page "Choosing what to build"³, before the builder opens an entry.
   - **How it fails.** Under the heading `## How it fails`, say in one sentence that the rbtv CLI can accept the thing and the thing can still fail. Then give the failures of step 2 as a list: one item for each failure, with what is wrong in the thing and what it causes. The first sentence says once that the rbtv CLI accepts the thing: do not end an item of the list, or the sentence after a weak line, with it again. The failure that the nearest kinds of thing do not have is in the list.
   - **What it is composed of.** Name the files that the author writes and their folder. Name each part that the author decides about, say whether the thing always has it, and say what the part does for the thing. Leave how to write a part to the part's own entry. Link a schema that a CLI loads, and do not list its fields. Say what the author decides for a field only where a step needs it.
   - **How to build it: the first step.** It makes the builder name three things: the failure that its own instance corrects, the cause of the failure, and the situation where the instance is used. Then the builder writes the purpose of the instance, based on the failure: what the instance does so that the failure does not happen. A builder that starts from the parts builds a thing that has every part and corrects nothing. Do not give the builder these words. Say what a failure, a cause and a situation are for this kind of thing, and where the builder finds each one. For a skill, the cause is something that the agent lacks. For a rule, it is a point in the work that the agent does not notice. For a capability, it is what the file that routes to it has passed on by then. When the step announces a number of items, list that number, and use the same names for them later. When the entry of an overlapping thing already has this step for the same work, follow rule 3 of "Which entry owns what".

     Weak, in the rule entry: "Before you write a line of the rule, write what goes wrong today, why it happens, and the situation."

     Strong: "Find the fault that the agent repeats from task to task and that its owner corrects again in each conversation. Its cause, for a rule, is a point in the work that the agent does not notice: write what the agent can observe when that point comes."

     The weak line is true of every kind of thing, so the builder of a rule learns nothing from it. The strong line says where the failure of a rule is found and what its cause looks like.
   - **How to build it: the next steps.** Write one step for each decision of step 3, in the order of the builder's work. Write each step as an order. Give it the fact that forces the decision as its reason, in the same sentence or in the next one: "do this, because the rbtv CLI does that with it". Give it its criterion when the step takes judgment. When a step is also true of the other cognitive units, it belongs to the page "Cognitive unit": reference that page at the step, and write only what your thing adds. Answer each failure of step 2 with one instruction, or record why it needs none.

     Weak, in the command entry: "Name every input, and say what the agent does when one is missing."

     Strong: "The human types the inputs after the name of the command, before the agent has read the body. Name each input in the words that the human types. When one is missing, have the agent stop and say what the next invocation has to carry, because a question at that point asks for what the human could have typed."

     The weak line stands unchanged in the entry of a skill and of a capability. The strong line is written from what is hard in a command: who gives the inputs, and when.
   - **The weak line and the strong line.** Where the failures list shows that one point of a step is often done wrong, show that point twice inside the step, as on this page: `Weak:`, then `Strong:`, then one or two sentences on what the weak line causes. Write the strong line first, complete, as the builder should write it. The weak line is the strong line with one decision made badly: a plausible mistake that the rbtv CLI accepts, never a caricature. Never shorten the strong line so that the two lines look alike: a strong line that lost its second half teaches half of the decision. Show one point, never a whole instance. After the two lines, say what the weak line causes, and stop. Do not add a sentence that tells the builder not to copy the lines, or one that says in what the two lines differ: the lines show it.
   - **The other kinds of work.** Give editing, converting and reviewing an instruction only where that work has a failure of its own. For editing, say which copy the author changes, and when the change reaches the reader. For converting, say where each part of an outside document goes. When a part is another kind of thing in rbtv, send the builder to the page "Choosing what to build".
   - **Facts of the rbtv CLI.** Two kinds of fact are easy to confuse. Keep the first and move the second.

     | The fact | Its place |
     |---|---|
     | What the rbtv CLI does with the thing, and so what the agent receives: a copy, a file that points to the source, a body without its frontmatter | in the entry, as the reason of the instruction that it decides |
     | How to run the rbtv CLI, and what the rbtv CLI enforces by itself: a command to type, a flag, who writes which field, the text of a refusal, the form of a name that the rbtv CLI refuses, a file name that the rbtv CLI passes over | in the page "rbtv CLI"⁷, or in the entry of the record. In those pages, these facts are the content. |
   - **Checks.** End "How to build it" with `Checks:` and three kinds of line, in this order. First, what a reviewer sees in the finished thing and no CLI enforces, each written as what is seen when it passes. Second, that the rbtv CLI accepts the thing, with what its acceptance shows for this kind of thing and what it does not show. Third, one try on a real task, with what to look at in the result.
   - **Template.** Give the layout of the one file as a code block that names its format. Each placeholder, in `<angle brackets>`, names the decision made at that place. A schema that a CLI loads stays a file, in the place and the format that the CLI expects.
   - **References.** Name another page by its title in quotes, with a raised number, at its first appearance, when that page can change what the builder does. The number is the row of the page in the table of references. Add a new reference at the end of the table, so that no number changes. Write each link relative to the final place of the entry. Write `must` only when no work on the thing can be done without that page, because `must` makes every reader open it. Otherwise write `when`, with the point in the builder's work, and say what the builder takes from the page.
   - **Then test the content.** Apply the three tests of "Steps written from the thing". Then, for each step, ask whether a builder can carry it out and still build a thing that fails. When the answer is yes, add what the builder has to understand, not another step. Then apply the tests of scaffolding language to each sentence. Delete a sentence only when the builder would do the same without it, and never to make the entry shorter.

5. **Check every reference.** Follow each link from the final place of the entry with a file listing, not from memory. Open each destination and compare it with your facts. A page that does not exist, or that contradicts the rbtv CLI or a decision of the owner, fails the row. Correct that page in the same change when the correction is one fact. Otherwise report it.

6. **Test the entry by its kind.** Launch fresh agents, on the cheapest model that will use the entry, as the skill "Sub-agents" says. Each has the entry and the pages that it links, a job as a user would write it, and a folder with everything that the job needs. It has neither this page, your record, nor an older page.
   - For a thing that the rbtv CLI adds, six runs: create one; convert an outside document of that kind that has one part with no place in rbtv; review an instance that the rbtv CLI accepts and that carries two failures of your list. Twice each, because one run shows one reading of the entry.
   - For a record, a cognitive unit with sections or a folder: one create task. For a file that a CLI writes: one task that needs the file to show something else. For a standard: one text that breaks it. For a word only: ten sentences to sort, five that use the word and five that use the nearest words.
   - A run counts only when everything that its job needs was in the agent's folder, and the agent could not reach the expected answers.
   - A run passes when the rbtv CLI accepts what was built, no failure of your list is in it, and it copies no weak or strong line of the entry. A review passes when it finds both failures.
   - Treat each failed run that counts as a defect of the entry. Find the sentence that is missing, wrong or was not read, repair it, and run that task again with a fresh agent. When the same task fails twice after repairs, stop and report both results.

- When you edit an entry: rewrite the sentence as if it had always read that way. An entry describes rbtv as it is, and what changed belongs to the decisions file. Repeat steps 5 and 6 for what the edit touches.
- When you convert an older page or an outside document into an entry: never take the source as the outline, because its headings invite parts that this term does not have. Record, for each warning, test and decision of the source, whether you kept it, referenced it or dropped it, and why. What one writer drops without a record, nobody sees.
- When you review an entry that you did not write: apply the three tests of "Steps written from the thing" and the checks below, then run one task of step 6.

Checks:

- The first sentence defines the term alone. The purpose says what the thing is for and when an author wants one. The part "How it fails" lists each failure with what it causes.
- The entry has no whole instance of the thing. Each weak line is its strong line with one decision made badly, and no strong line is shortened.
- "How to build it" opens with the failure, its cause and the situation, each said for this kind of thing, then the purpose based on the failure. Each later step is an order with its reason, and each step that takes judgment states its criterion.
- No sentence of "How to build it" is still true with a neighbouring term in place of the entry's term.
- No sentence of eight words or more is also in this page, in its template or in the entry of a neighbouring term.
- Three sentences on what a builder has to get right could not be about another term.
- No sentence says which other kind of thing to build.
- No command to type, flag, text of a refusal, form that the rbtv CLI enforces or file name that the rbtv CLI passes over is on the page of a thing that an author writes.
- Each decision of your list of step 3 is in the entry, as a step or as the reason of a step. The entry of a kind has no step whose only content is that the shared page says it, and no sentence says how the pages are divided or announces what the entry adds.
- In the entry of a thing that has sections, each section has its part in the one fixed shape.
- No instruction and no check is also in a page that the entry references, and the entry defines no term but its own.
- Every page that is named has its title in quotes and the number of its row, and every row is named in the text. Every link leads to a file from the final place of the entry.
- The two searches of scaffolding language return no match in the entry. No sentence has three clauses that begin with "that", "which" or "whose".
- The tasks of step 6 pass.

## Template

````markdown
# <Term>

<One sentence that defines the term in rbtv and can be read alone. Where the version of rbtv differs from the outside one.>

<What the thing is for. When an author wants one. One order that says what a well-built thing achieves.>

## How it fails

<One sentence: the rbtv CLI can accept it, and it can still fail.>

- <One failure: what is wrong, and what it causes.>
- <One failure that the nearest kinds of thing do not have.>

## What it is composed of

<The files that the author writes and their folder. Each part: always or under which condition, and what it does for the thing. The link to a schema that a CLI loads.>

## How to build it

1. **<The failure, its cause and the situation, then the purpose.>** <What each of the three is for this kind of thing, and where the builder finds it. The purpose is based on the failure.>
2. <One decision that is hard in this thing, as an order, with the fact that forces it as its reason, and its criterion when the step takes judgment.>

   Weak: <the point of this step, as it is often written>

   Strong: <the same point, with the one decision made well>

   <What the weak line causes.>

- <When you edit, convert or review: an order with its reason, only where that work has a failure of its own.>

Checks:

- <What a reviewer sees in the finished thing when it passes, and no CLI enforces.>
- <The rbtv CLI accepts it: what that shows for this thing, and what it does not show.>
- <One try on a real task, and what to look at in the result.>

## Template

```<format>
<the layout of the one file, with a placeholder for each decision>
```

## References

| # | Page | File | Read | When | To |
|---|---|---|---|---|---|
| 1 | <title> | [<title>](<path from the final place of the entry>) | must | | <what the builder takes from the page> |
| 2 | <title> | [<title>](<path from the final place of the entry>) | when | <the point in the builder's work> | <what the builder takes from the page> |
````

## References

Files are given from the `capabilities/` folder of the component that contains this page, except the last two, given from the repository root.

| # | Page | File | Read | When | To |
|---|---|---|---|---|---|
| 1 | Scaffolding language | `glossary/scaffolding-language.md` | must | | word every sentence of the entry, and apply its tests |
| 2 | Cognitive unit | `glossary/cognitive-unit.md` | when | the entry is of a skill, a rule, a command or a prompt, or a step is also true of those | reference what all of them have in common, and write only what the thing adds |
| 3 | Choosing what to build | `_under-evaluation/guides/procedure documents/choosing-what-to-build.md` | when | you are about to write which other kind of thing to build, or a part of a converted document is another kind of thing in rbtv | send the builder to that page |
| 4 | Routing table | `glossary/routing-table.md` | when | the thing has a description, or routes to other files | have the builder write a row, and say what each part contains for this thing |
| 5 | Component | `glossary/component.md` | when | deciding which component's glossary owns the term | find the glossary folder |
| 6 | Schema | `glossary/schema.md` | when | the thing is a file that a CLI checks | find the schema file and the CLI that loads it |
| 7 | rbtv CLI | `glossary/rbtv-cli.md` | when | you are about to write a command to type, a flag or a refusal, or to have the rbtv CLI accept an instance | place that fact there, or find the command to run |
| 8 | Functions | `meta/functions/skills/` | when | step 1, what the user expects is not written, or how the thing works today has to be found | use `interview` or `investignosis` to agree with the user |
| 9 | Sub-agents | `meta/sub-agents/skills/sub-agents.md` | when | launching the first build of step 2 or a run of step 6 | launch a fresh agent that has only what you give it |
