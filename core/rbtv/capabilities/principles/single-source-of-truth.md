# Single source of truth

Single source of truth means each fact, each instruction, each setting and each operation is edited in one file, the home, and every other file points to that home, even when writing the fact again in the file that is open would be easier for its reader. Outside rbtv the same rule is applied to data: a record is edited in one place, and a copy of it is read and not edited. Here the home is a file that an agent reads. A term's meaning is one such fact. The page "Terminology is king"¹ says how that meaning is defined, how a deviation from it is corrected, and how an agent reaches the entry.

Two copies of a fact stop agreeing as soon as one of them changes. An agent that reads one of them cannot tell which file is the home, so it acts on the copy it read. Apply the rule when you are about to write a fact, an instruction, a setting or an operation, and when a sentence states a fact that another file owns. Apply it so that a change to the fact is one edit, and a reader of any other file reaches that same fact.

## How it fails

The program can accept every file, and a fact can still have two homes. It does not compare one file with another.

- The fact is written again in the file that is open, because that file's reader needs it, and another file already states it. The two stop agreeing at the next edit of one of them. The agent acts on the copy it read.
- The fact is new, and its home is the file that is open, not the file that changes when the fact changes. A fact about what the program reads, written into each glossary entry, is not updated when the program changes, because that entry was not in the change.
- A sentence has to state the fact to be understood, and the statement does not use the home's words. The sentence is accepted and still fails. A later edit of the home does not touch it, and a reader cannot tell which sentence matches the home.
- Two files each have the instructions that both of them need, or each has its own steps for one operation. The next edit updates one file.
- A list of a kind of state is kept by hand. The home of that state changes. The list does not. The program does not compare them.
- The part that the program writes into a file that a harness reads is edited. The program overwrites that edit when it next writes that part. Until then, the agent reads text that the home does not say.

## How to apply it

1. **Name the fact, the file that changes with it, and the file that is open.** The file that is open is not evidence that the fact has no home. Search for a file that already states the fact, including a file in another component. The search is for that statement, not for a word. A word with two meanings is the page "Terminology is king"¹. When a home exists, link it. Do not write the fact again. A link is not a second home. How a route names the file is the page "Entry point"².

   Weak: "Write the field list in this page, so a reader does not have to open another file."

   Strong: "Link the page that has the field list. Name a field here only where a step uses that field."

   The weak line writes the list again, because the reader of this page needs it. The next edit of the list does not touch this page.

2. **When no home exists, put the fact in the file that changes with it.** Ask which other facts change for the same reason, and which file a writer changes when those facts change. That file is the home. A fact about what the program reads changes when the program changes, together with the other facts about what the program reads and writes. How the program is run, and what it enforces by itself, have their home in the page "rbtv command"³. A fact of the program that decides what an author writes stays in the page of that thing, as the reason of the instruction that it decides. When the files are glossary entries, the page "Writing a glossary entry"⁴, in the part "Which entry owns what", applies this rule. Do not restate its five rules.

   Weak: "Add how the program recognizes a skill to the skill page, so the builder has it in the page that is open."

   Strong: "How the program recognizes a skill changes when the program changes, together with the other facts about what the program reads. Put it on the page "rbtv command"³, and link that page from the skill page."

   The weak line picks the file that is open. The next change to the program updates one page and leaves the skill page unchanged.

3. **When a sentence cannot be understood without the fact, state the fact in the words of its home, and link the home.** Do not use other words for it. When this text and the home do not say the same thing, change this text in the same change. Do not change the home to match this text. One word for one thing, inside one text, is the page "Scaffolding language"⁵. This step governs a fact that another file owns, not the word used for it.

   Weak: "The limit is about ten."

   Strong: "The limit is ten."

   The weak line says the home's sentence in other words. A later edit of the home, from ten to twelve, does not touch "about ten", and a reader cannot tell which sentence matches the home.

4. **When a second file needs content the first has, move that content to one home and point both files to it.** Writing the content again in the second file makes a second home. The next edit of the first does not touch it. When both files are cognitive units, the page "Cognitive unit"⁶ says where that shared text goes. When no page has settled the kind of the home, decide it with the page "Choosing what to build"⁷. Do not write the home into each route. More than one route can name the same file, as the page "Capability"⁸ states.

   Weak: "Copy the steps into the command, so a reader of the command does not open the skill."

   Strong: "Move the steps to one file. The skill and the command both name that file."

   The weak line keeps two homes so that one reader does not follow a link.

5. **Give each operation one implementation.** Every way to perform it calls that implementation. A second set of steps is a second home. When one way is for a human and one way is for an agent, both call that implementation. The page "Agent parity"⁹ says how each way reaches it. Do not write the steps in both ways.

   Weak: "The screen saves the setting with its own checks, and the command saves the setting with its own checks."

   Strong: "The screen and the command both call the same save operation. Each keeps only a check that its own way needs. The save does not have that check."

   The weak line is two implementations. They stop agreeing at the first change to one check.

6. **Keep each kind of state in one home.** A view of that state reads that home. A list kept by hand is a second home. Where an installation keeps its settings, and what reads them, is the page "rbtv command"³.

   Weak: "Keep a list in the readme of what is installed, and update that list when the home changes."

   Strong: "The readme links the home of what is installed. It does not list what is installed."

   The weak line is a view kept by hand. The home changes. The list does not. The program does not compare them.

7. **Do not edit the part that the program writes into a file that a harness reads.** The program overwrites that edit when it next writes that part. Change the file that the program reads. Text in the same file that the program does not write is not this case. The page "rbtv command"³ says which part the program writes, and how the program writes it again.

   Weak: "Correct the rule in the part that the harness file marks as generated, because that is the text that the agent follows."

   Strong: "Correct the rule in the file that the program reads. The part marked as generated is overwritten when the program next writes that part."

   The weak line edits the generated part. Until then, the agent reads text that the home does not say.

- When you edit a fact, edit the home. In the same change, correct every other text that states the fact and now disagrees. A text that only links the home needs no edit of the fact. This page does not say what to delete from the home.
- When you review, take one fact and open the home and one other file that uses it. A review that reads only the file that is open misses a second copy.
- When you convert, put each fact of the outside document in the home that this page picks. Do not write that fact into every file that mentions it. If a converted part belongs to another page, decide that with the page "Choosing what to build"⁷.

Checks:

- A reviewer sees one home for the fact. Every other mention links that home, or states the fact in the home's words and links the home. An operation has one implementation. A kind of state has no list kept by hand. The part that the program writes for a harness has no hand edit.
- The program accepts the files. Acceptance does not show that a fact has one home, and it does not show that a generated part was left unedited.
- Change one fact in its home, then read a second file that uses it. The second file still agrees with the home, or it links the home and does not carry the old words. Then change only the second file. The home is unchanged, so the second file is the one to correct.

## References

| # | Page | File | Read | When | To |
|---|---|---|---|---|---|
| 1 | Terminology is king | [Terminology is king](terminology-is-king.md) | when | the fact is a term's meaning, or the search is for a word | take how the meaning is defined, how a deviation is corrected, and how an agent reaches the entry |
| 2 | Entry point | [Entry point](../glossary/entry-point.md) | when | a route names the home | write the row that names the home |
| 3 | rbtv command | [rbtv command](../glossary/rbtv-command.md) | when | the fact is what the program reads or writes, or a part that the program generates | take the home of those facts, which part is generated, and how that part is written again |
| 4 | Writing a glossary entry | [Writing a glossary entry](../writing-a-glossary-entry.md) | when | the files are glossary entries | apply the part "Which entry owns what", and do not restate its five rules |
| 5 | Scaffolding language | [Scaffolding language](../glossary/scaffolding-language.md) | when | the question is one word for one thing inside one text | take the wording, and leave a fact that another file owns to this page |
| 6 | Cognitive unit | [Cognitive unit](../glossary/cognitive-unit.md) | when | the same instructions serve a second cognitive unit | take where that shared text goes |
| 7 | Choosing what to build | [Choosing what to build](../choosing-what-to-build.md) | when | no page has settled the kind of the home, or a converted part is another kind of thing in rbtv | decide the kind |
| 8 | Capability | [Capability](../glossary/capability.md) | when | the home is named by more than one route | take that more than one route can name the same file |
| 9 | Agent parity | [Agent parity](agent-parity.md) | when | one way to perform an operation is for a human and one way is for an agent | take how each way reaches the one implementation |
