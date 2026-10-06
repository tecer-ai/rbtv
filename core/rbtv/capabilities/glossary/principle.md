# Principle

A principle is the one page for a design choice that a builder applies before the design is written, whatever the kind. Outside rbtv a principle is often a preference of one good over another. Here the page is a test. A reviewer confirms or rejects a design from the first sentence. That sentence is plain.

The skill "framework"¹ names the page on every reading, before the other rows. A builder applies the test on that reading, before a design.

A principle is a test of a design, not the page that defines a term. The page "Writing a glossary entry"² is the page of a term. A principle is a capability: a row of the skill "framework"¹ names it on every reading, and a builder applies it before the design. The page "Capability"³ says what a capability is.

A principle is for a design choice that builders would make again, and would make differently, each time they write a file. An author wants one when the choice applies to more than one kind of file, and no page that the skill "framework"¹ already names on every reading decides the choice. The page "Choosing what to build"⁴ decides whether the content is a principle. Write a principle so that a builder rejects a broken design. The builder keeps a design when the design meets the choice. The builder has the page, and the design is not yet a file. The same decision applies to a second kind of file.

## How it fails

The rbtv CLI can accept the component, and the principle can still fail as a test of a design. A file under `capabilities/principles/` is not among the files it reads.

- The first sentence is a preference of one good over another, or it names a quality. A builder cannot say whether a design meets the sentence.
- The page explains why the choice is worth making, and no check names what a reviewer sees in a design. The builder agrees, and still cannot reject a design.
- A step or a check requires a section, a field or a file in every design. A design that meets the choice without that part fails the page.
- A sentence orders the agent at a moment of the task. The page is not in front of the agent then, so the task is done without the order.
- The first lines name when to open the file. The skill "framework"¹ has already opened it, on every reading. The builder looks for a task that matches, finds none, and does not apply the test.
- The page is the method of one kind, or it repeats a test that another principle already decides. Every reading carries a test that only one kind can fail. Two pages decide one choice, and a later design follows one page and misses the other.
- The file sits in that folder and the skill "framework"¹ does not name it. No reading opens the file.

## What it is composed of

Write one markdown file, `capabilities/principles/<name>.md`, in the component `core/rbtv`. Name it in lower case with hyphens, matching the link in the every-reading row of the skill "framework"¹. Write no frontmatter. Every reading loads the file from that row, not from a description in the file.

The parts are the ones that the page "Writing a glossary entry"² names for a principle, in that order. Do not list those parts on this page again. A link to another principle in the same folder uses that file's name. A link to a page under `glossary/` starts at `../glossary/`, because this file stays in `capabilities/principles/` and nothing copies it out.

There is no `principles.md`. The page "Progressive disclosure"⁵ refuses an index of that folder. The skill "framework"¹ names each principle. A principle of rbtv lives in that folder of that component.

## How to build it

1. **The choice, the cause and the two designs, then the purpose.** Before you write a line of the file, name the design choice that builders make differently. The cause, for a principle, is a choice that applies to more than one kind of file. No page that the skill "framework"¹ names on every reading decides the choice. The situation is two designs of two kinds. The builder has not written either design. Then write the purpose from the choice. The purpose is the decision both designs get from this page, so the choice is not made again. When you cannot name a second kind, or a named page already decides the choice, stop. When the cause is a point during a task, a term with no page, or work a route did not pass, stop in the same way. The page "Choosing what to build"⁴ decides the file. An author who starts from the headings names no choice, so the file corrects no design.

   Weak: "The choice is remade each time a skill is written and each time a command is written. No page that is named on every reading decides it. The builder has not written either file. The purpose is that the skill gets the decision from this page."

   Strong: "The choice is remade each time a skill is written and each time a command is written. No page that is named on every reading decides it. The builder has not written either file. The purpose is that the skill and the command get the same decision from this page."

   The weak line names a second kind and then leaves it out of the purpose, so a command that breaks the choice passes. Every reading still carries the page.

2. **State the choice in a plain sentence, and say what the page is for.** The first sentence names what a reviewer confirms or rejects in a design. Name the case in which the choice still applies, in that sentence or the next. Do not use the form "X, even over Y". A quality is not the sentence. The following lines say what the page is for. A builder applies the page before the design is written. Do not open by naming when to open the file. The skill "framework"¹ has already opened it. Apply the page "Scaffolding language"⁶ to every sentence.

   Weak: "Prefer a named file in the report, even over a short report."

   Strong: "The report names the file and the line. The choice still applies when a shorter report would be easier to skim."

   The weak line gives a preference. A builder who would not choose the short report cannot say whether a design meets the sentence.

3. **Write each failure, each step and each check as a test of a design.** Write the failures, the steps and the checks as the page "Writing a glossary entry"² says, each about a design and not about a task. Do not require a section, a field or a file that the choice does not require. Do not write an order for a moment of the task. That order is the failure above.

   Weak: "Every design has a Report section. The agent writes the file name there before it saves."

   Strong: "A reviewer rejects a design whose report names no file. The page does not add a section to the design, and it does not tell the agent what to do at the save."

   The weak line rejects a design that meets the choice and has no Report section. The order at the save never reaches the agent.

4. **Name the file from the skill "framework", on every reading.** Add a row to the skill "framework"¹. Put the row among the rows that every reading loads. Put it before the rows that name a condition. The rbtv CLI does not read this folder. Without a row that says every reading of the skill "framework"¹, no builder applies the test before a design. Do not write `principles.md`, because a list of the folder is not a route. The page "Routing table"⁷ has the columns. For this row, `CONTAINS` names the test, `PURPOSE` names what a design does when the test is met, and `ALWAYS LOAD WHEN` is every reading of that skill. Leave `DO NOT LOAD WHEN` empty. There is no reading of that skill that must not apply the test.

   Weak: "Add the file under principles/, and list it in principles.md."

   Strong: "Add a row to the skill "framework"¹. Put the row among the rows that every reading loads, and before the rows that name a condition. `CONTAINS` names the test. `PURPOSE` names what a design does when the test is met. `ALWAYS LOAD WHEN` is every reading of that skill. Leave `DO NOT LOAD WHEN` empty."

   The weak line puts the file where no reading opens it. A list of the folder is not a route.

5. **Keep one choice, and write a test that a second design can fail.** Read the pages that the skill "framework"¹ names on every reading. When one of them already decides the choice, change that page. The page "Single source of truth"⁸ is where a second copy is refused. Do not write a second file. When two of those pages both apply to one design, the page "Keep it stupidly simple"⁹ decides. Write no tie-break in this file. Write the test so a design of a second kind can fail it. A test that only the prompting case can fail is a note of that case. When the material is one occurrence from a conversation, the page "Tips development"¹⁰ says that the occurrence is not this file.

   Weak: "This page rejects a report that names no file, in a skill. A command is out of scope."

   Strong: "This page rejects a report that names no file, in a skill and in a command."

   The weak line limits the test to one kind. Every reading still carries the page, and a command with a report that names no file passes.

When you edit, change the source file. The next reading of the skill "framework"¹ sees the edit, because that reading opens the source. When the row no longer names the test that the file states, change the row. The page "Routing table"⁷ says how the row is changed.

When you convert an outside principle, or a file whose headings are Statement, Rationale and Implications, do not keep those headings. The statement becomes the plain sentence when a reviewer can confirm or reject a design from it. Drop a rationale that names no design to reject. A sentence that orders the agent at a moment of the task is not a step of this file. Stop. The page "Choosing what to build"⁴ decides where that sentence goes. An implication that adds a section to every design is rewritten as a test of the design, or dropped.

When you review, apply the file to a design that breaks the choice in two ways. Report each break as what is wrong in the design and what the break causes. If the only report is acceptance of the component, the principle was not reviewed.

Checks:

- The first sentence states the choice in words a reviewer can confirm or reject in a design. It is not a preference of one good over another, and it does not name a quality. The lines after it say that a builder applies the page before the design is written. The file has no frontmatter, and it does not open by naming when to open the file.
- A check names what is seen in a design when the choice is met. No check requires a section, a field or a file that the choice does not require. No sentence orders the agent at a moment of the task. The file does not repeat a test from the every-reading list of the skill "framework"¹. It states no tie-break.
- The skill "framework"¹ names the file. The row sits among the rows that every reading loads, before the rows that name a condition. There is no `principles.md`.
- Where the rbtv CLI accepts the component, acceptance shows that the component was found. It does not show that a builder can reject a design from this file before the design is written. It does not show that the skill "framework"¹ opens the file on every reading. The page "rbtv CLI"¹¹ describes that run.
- Give a builder the file and a design that breaks the choice in two ways. One break is a part that the choice does not require, or an order for the agent during a task. The other break is the same choice failed in a second kind of file. Apply the file. Both breaks are corrected, and the design gains no section the choice does not require.

## References

| # | Page | File | Read | When | To |
|---|---|---|---|---|---|
| 1 | framework | [framework](../../skills/framework.md) | when | adding the row, or checking that every reading names the file | take that each principle is named there, on every reading, before the other rows |
| 2 | Writing a glossary entry | [Writing a glossary entry](../writing-a-glossary-entry.md) | must | | take the parts of a principle, in order |
| 3 | Capability | [Capability](capability.md) | when | the file would continue a route, or would open with what a route passed | take what that file is, and do not write this file as that continuation |
| 4 | Choosing what to build | [Choosing what to build](../choosing-what-to-build.md) | when | the cause is a point during a task, a term with no page, or work a route did not pass, or a named page already decides the choice, or a converted sentence is another kind | decide the file |
| 5 | Progressive disclosure | [Progressive disclosure](../principles/progressive-disclosure.md) | when | about to write an index of the principles folder | take that an index of the folder is refused |
| 6 | Scaffolding language | [Scaffolding language](scaffolding-language.md) | must | | word every sentence |
| 7 | Routing table | [Routing table](routing-table.md) | when | writing or changing the row in the skill "framework" | take the columns, and how a row is changed |
| 8 | Single source of truth | [Single source of truth](../principles/single-source-of-truth.md) | when | a page on the every-reading list already decides the choice | leave the choice in that page |
| 9 | Keep it stupidly simple | [Keep it stupidly simple](../principles/keep-it-stupidly-simple.md) | when | two principles both apply to one design | take the decision, and write no tie-break here |
| 10 | Tips development | [Tips development](../tips-development.md) | when | the material is one occurrence from a conversation | take that the occurrence is not this file |
| 11 | rbtv CLI | [rbtv CLI](rbtv-cli.md) | when | a run accepts the component | take what acceptance shows for this file |
