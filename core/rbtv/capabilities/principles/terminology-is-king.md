# Terminology is king

Terminology is king means one term for one meaning, and the glossary entry of the term defines that meaning. It applies even when a shorter or more familiar word would be easier to write. Outside rbtv, a shared vocabulary allows a second word for the same thing, and the same word may mean one thing to one team and another to another. Here the reader is an agent. It acts on the word it read, and it cannot ask which sense was meant. A second word is a second thing. A second sense is two things under one name.

The glossary entry of the term is its one home. Apply this page to the name. Follow the page "Single source of truth"¹ when a sentence states a fact that the entry owns.

An author applies this page before naming a concept, a folder, a file or a field, before writing a word that the glossary defines, and when a term's meaning changes. Apply it so that an agent that opens the glossary entry gets the one meaning. A file that uses another word for that thing is corrected to the term.

## How it fails

The rbtv CLI can accept the file, and the names can still fail. It does not read the words of a page. It exposes a file from a source folder that it scans. A folder with another name is not exposed.

- A shorter word stands in for the term. The reader takes the shorter word as a second thing, or as the term with a piece of it left out.
- The file that uses the term also writes what the term means. The next change of the glossary entry does not change that sentence, so the agent can act on the old meaning.
- A second name sits beside the term, including a word kept so that nothing breaks before a later change. The reader follows one name and misses the other, or treats the two names as two things.
- The term is used in its ordinary sense, or one plain word is made to cover several things that already have terms. The reader merges two things, or cannot tell which thing the word names.
- A folder, a file or a field is named with a harness word or with a shorter word. The rbtv CLI does not scan that folder, so the file is not exposed. A wrong word in a page is accepted.
- The meaning changes in the glossary entry, and a current file keeps the old meaning. The old sentence still reads as ordinary language, so the agent acts on it.

## How to apply it

1. **Find the name that the agent will misread, then search the glossary files.** Before you write a name, find the word in the request, or in the file, that names a thing that another file also names. A later task that has to mean the same thing by that word also needs the shared term. When the word is not the glossary term, the agent treats one thing as two. When the glossary term is used in another sense, the agent merges two things. The word is there because a shorter or more familiar word was easier to write, or because this file was about to define the thing. The agent is reading the file in the middle of a task, and it cannot ask.

   A word is a term when two files, or a file and a later task, have to mean the same thing by it. Search the glossary files for the thing. The entry is the file named after the term. When the glossary has the term, use that term. Do not take the request's word as the name. When no entry has the thing, and two files have to share the name, the glossary entry exists before any other file uses the name. Write that entry as the page "Writing a glossary entry"² says. An rbtv term has its one entry in the rbtv glossary. A word that names a subject of one component, and is not an rbtv term, has its one entry in that component's glossary. One word has one entry. Do not give an rbtv term a second meaning in a component.

   A word that one file uses once, in its ordinary sense, or as a search hint so a person can find a note, is not a term. Do not give it an entry, and do not replace it with a glossary term. Word that sentence as the page "Scaffolding language"³ says.

   Weak: "Give the agent the job."

   Strong: "Give the agent the task."

   The weak line takes the request's word and skips the glossary. The reader can treat job and task as two things.

2. **Use the term whole.** Write cognitive unit, not unit. The shorter word is a second word.

   Weak: "A rule is the unit."

   Strong: "A rule is a kind of cognitive unit."

   The weak line cuts the term. The reader takes unit as the thing, or as a second thing.

3. **Use the term only in the meaning that its glossary entry gives it.** For anything else, use a plain word that no entry defines. Do not make a term of a word that would have to cover several things. Name each thing by its term, or use a plain word. The rbtv CLI does not read which sense you meant.

   Weak: "The step runs the command that lists the files."

   Strong: "The step runs the CLI that lists the files."

   The weak line uses the term for a CLI. The reader merges the CLI and the cognitive unit.

4. **Do not write what the term means in the file that uses it. The one exception is the page "Single source of truth": when a sentence cannot be understood without the meaning, state it once in the words of the entry, and link the entry.** Use the term, and send the reader to its glossary entry. An agent opens the entry from that route, and it does not need a definition written in this file. A definition in this file stays when the entry changes, so the agent can act on the old meaning. Write the route as the page "Routing table"⁴ says.

   Weak: "A skill is a cognitive unit that the agent opens from a description. Then write the steps."

   Strong: "Open the glossary entry of skill, then write the steps."

   The weak line writes the meaning in the file that uses the term. A later change of the entry leaves that sentence.

5. **Name a folder, a file and a field with the term.** Do not name them with a harness word, and do not name them with a shorter word. The rbtv CLI reads a command from the source folder `commands/`. For Codex it writes that file under the harness folder `prompts`. It does not scan `prompts/`, so a file placed there is not exposed. The page "rbtv CLI"⁵ has the other source folders and the paths that the rbtv CLI writes. A wrong word in a page, or in a field that the rbtv CLI does not read, is accepted.

   Weak: "Put the file in prompts/, the name that Codex uses for a command."

   Strong: "Put the file in commands/."

   The weak line uses the harness word as the folder name, so the rbtv CLI does not expose the file.

6. **When the name or the meaning changes, change the entry and every current file in the same change.** Search the current files for the old word and for the old meaning. A sentence that still reads as ordinary language can still carry the old meaning. Do not leave the old word in a page that an agent reads in order to act, so that nothing breaks before a later change. That leftover word is a second name. Do not add a line that the old word still means the term. A record of a decision already made keeps the words of that decision. Do not rewrite that record to the new word.

   Weak: "Change the glossary entry now. Leave unit in the other files until the rbtv CLI changes."

   Strong: "Change the glossary entry and every current file that says unit, in the same change. Those files say cognitive unit, and they do not also say unit."

   The weak line keeps the old word until every file is changed. The reader meets both words and treats them as two things.

- When you edit: search the file for a shorter word, a second name, and a sentence that writes what a term means. Replace the word with the term. Delete that sentence and send the reader to the entry. Do not add the old word to the entry as another name. A human and an agent both correct the word, because the term is the only name and the other word is visible.
- When you convert: an outside document's word is not the term. Map each name to a glossary term, or to a plain word that no entry defines. When a name is a new term, the entry exists before the converted file uses it. Do not keep the outside name beside the term.
- When you review: open the glossary entry of each term that the file names, and compare each name with that entry. A word that is not the term, a sentence that writes what a term means, and a folder named with a harness word are defects. Acceptance of the file is not that comparison.

Checks:

- A reviewer sees the glossary term, whole, in every current file that names the thing. No current file writes what a term means. No folder, file or field uses a shorter word or a harness word for a term. A changed meaning has no current file left on the old meaning. A record of a decision already made still has its own words.
- The rbtv CLI can accept a file whose words are wrong. Acceptance shows that a scanned folder and the checked fields matched, as the page "rbtv CLI"⁵ says. It does not show that the words are the terms. A file in a folder the rbtv CLI does not scan is not exposed.
- Take a page that uses a shorter word and a second name, with the glossary entry of the term. The corrected page uses the term whole, does not write what the term means, and does not add the old word to the entry. Then place a command. The file is in `commands/`, not in a folder named with a harness word.

## References

| # | Page | File | Read | When | To |
|---|---|---|---|---|---|
| 1 | Single source of truth | [Single source of truth](single-source-of-truth.md) | when | a sentence states a fact that the glossary entry owns | take what one home requires of that fact |
| 2 | Writing a glossary entry | [Writing a glossary entry](../writing-a-glossary-entry.md) | when | a term has no entry yet | write the entry, and find the glossary folder |
| 3 | Scaffolding language | [Scaffolding language](../glossary/scaffolding-language.md) | when | wording a sentence that uses a plain word, or that names a page | word the sentence, and take how a sentence names another page |
| 4 | Routing table | [Routing table](../glossary/routing-table.md) | when | sending the reader to the glossary entry from a route | write the route, and do not put the meaning of the term in the row |
| 5 | rbtv CLI | [rbtv CLI](../glossary/rbtv-cli.md) | when | naming a source folder, or having the rbtv CLI accept a file | take the source folders and the paths that the rbtv CLI writes, and what acceptance shows |
