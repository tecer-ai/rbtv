# Scaffolding language

Scaffolding language governs how every text of an agent's scaffolding¹ is worded, so that its reader understands at the first reading exactly what the writer meant, and knows what to do. Its goals are clarity, objectivity, eloquence, consistency and actionability. A shorter text is a by-product of these goals. It is never a goal.

The scaffolding is everything an agent is exposed to, its prompt included: a prompt, a skill, a rule, a command, folder instructions, folder artifacts and capabilities. The reader of such a text is an agent in the middle of its work, or the person who owns the text. Neither can ask the writer what a sentence meant. The agent acts on what it understood: a sentence that it misreads becomes a wrong action, and a sentence that it did not need takes its attention from the sentences that it needs.

Scaffolding language governs wording. It does not reduce what a text makes its reader think about. A text written in scaffolding language:

- still states what its subject is for, the situation in which it is used, and what its reader has to weigh;
- states a point that is subjective as an instruction or a fact that a reviewer can check;
- never leaves a point out because it is hard to word. A text that keeps only a list of files and steps is missing something that its reader needs.

## How to apply it

You know what each of your sentences was meant to say, so reading your text again does not show you which sentence fails. Apply the tests of each goal to each sentence.

**Clarity: the reader understands the sentence at the first reading, in the meaning that you gave it.**

- Name the thing and the action in their literal words. A figure of speech makes the reader translate, and two readers translate it differently. The test: read the verb literally, and when its subject cannot do that action, write the action that you mean. An established verb of computing or of editing passes the test: a file contains a field, a link points to a page, a program reads a file. Weak: "The summary is the front door of the report." Strong: "Put the conclusion in the first sentence of the summary, because most readers read only that sentence."
- Name each thing with an ordinary word, with a term of the glossary in its glossary meaning, or with a word that you define in the sentence that first uses it. A label that you invent sends the reader back through the text to find what it means.
- Use each word in the sense that a reader gives it first. A common word in a new sense passes the test of the literal verb and still stops the reader, who takes the usual sense and then has to correct it. Take the word that people already use for the thing, and write a verb where a noun only names an occasion: "when" in place of "the moment at which". Give no word two senses in one text or in two texts of one set. Keep "that" after a noun: "the file that the program writes", not "the file the program writes". Weak: "At each opening of the file, the opening says what a line is." Strong: "Each time an agent reads the file, its first lines say what a line is."
- Name another page by its title, in quotes, with the number of its row in the table of references, raised: the page "Writing a report"². A title that is used as a word of the sentence reads as part of the sentence. Weak: "Decide it with the capability choosing what to send." Strong: "Decide it with the page "Choosing what to send"³." Add a new reference at the end of the table, so that no number changes.
- Let a pronoun stand only for a noun that the reader can name without searching. Weak: "Compare the note with the list and correct it." Strong: "Compare the note with the list and correct the list."
- Write the step between a claim and the instruction that follows from it. After each claim, ask "why?" and "what does the reader do then?", and write each answer that the reader cannot supply.

**Objectivity: each sentence is a fact, a condition or an instruction that a reviewer can check.**

- Replace a request for a quality, an emphasis or a reminder with what a reviewer could observe. Weak: "Make sure the report is thorough." Strong: "State the result in the first sentence of the report, and list every file that you changed."
- Write a point that is subjective as the criterion that decides it. Weak: "Use good judgment about when to stop searching." Strong: "Stop searching when two searches in a row return nothing new."
- Check a claim about what a program or an agent does before you write it: in the program, in its help output, in the file itself, or in a run that you observed. A claim that is true of some cases names those cases.

**Eloquence: the text is fluent, connected prose.**

- Write complete sentences that follow from one another, and give each instruction its reason, in the same sentence or in the next one. A list of fragments gives the reader the steps and none of the reasoning that connects them.
- Put one statement in one sentence. Split a sentence at its third clause that begins with "that", "which" or "whose", and split one in which such a clause sits inside another. State the subject first. Weak: "The fault that a summary corrects is a report that a reader who has ten minutes does not finish." Strong: "A summary corrects one fault. A reader who has ten minutes does not finish the report."
- Give several faults, or several cases, one sentence each, or one item of a list each. A chain of "or" and "so" makes the reader keep every part in mind until the last one.
- Use a list for items of one kind. Use prose where one sentence depends on another.
- Do not repeat the subject in every sentence so that each one can be read alone. Weak: "The report names the file. The report gives the line. The report states the fault." Strong: "The report names the file, gives the line and states the fault."

**Consistency: one word for one thing, and one construction for one kind of statement.**

- Use the same word for the same thing in the whole text, and the glossary's term when the glossary has one. A second word for the same thing reads as a second thing.
- Write one kind of statement the same way each time: an instruction as an order, a condition with "when" before the instruction that it governs, a choice as "choose X when ...; otherwise Y".
- Consistency between two files is not a matter of wording: the page "Single source of truth"² governs a fact that another file owns.

**Actionability: after each sentence, the reader knows what to do, or knows a fact that changes what it does.**

- Write an instruction as an order to the reader, with its reason. Do not soften it and do not narrate it, because the reader takes a softened or a narrated sentence as optional. Weak: "The report should ideally be sent before the task is closed." Strong: "Send the report before you close the task, because nobody reads a report that arrives after the decision."
- Say when an instruction applies, unless it applies always.
- State the purpose before the first instruction, and give an instruction its reason when the reason decides a case that the instruction does not name. A reader that has only the steps cannot decide such a case.

**The by-product: a shorter text.**

- Delete a sentence when the reader would do the same without it, because it takes attention from the sentences that the reader needs. Complete "without this sentence, the reader does ...". When the answer is "the same", delete the sentence.
- State a fact once in a text. Each copy passes the test above alone, so search the text for the fact.
- Never delete one of these, and never shorten it until it says less: a fact that changes what and how the reader decides; the purpose of the thing, or the situation that it is for; a step of reasoning that the reader cannot supply; a decision that you made and that the reader would otherwise make differently; a reason without which the reader would apply an instruction to a case that it does not cover, or would not apply it to a case that it covers.
- Never judge a text by its length. Before you cut a sentence, name what the reader loses with it. When the reader loses something, the sentence stays.

Checks:

- This search, ignoring case, returns no match outside a quoted weak line or a copy of the pattern. Each word in it names a quality or asks for care, and names nothing that the reader can do.

```text
\b(clear|clearly|concise|robust|proper|properly|appropriate|appropriately|effective|effectively|comprehensive|high-quality|well-structured|important|crucial|essential|very|really|ensure|make sure|be careful|carefully|remember to|note that|keep in mind|best practices?|simply|seamless|leverage)\b
```

- This second search, ignoring case, returns no match outside a quoted weak line or a copy of the pattern. Each word in it was used in texts of the scaffolding in a sense that readers did not expect, and an ordinary word says the same.

```text
\b(openings?|holds?|held|holding|the lack|the moment at which|moments? at which|behind (a|an|one|the|each)|only looks right|stated from|takes? for|the send|landing|arrivals?|a time (that )?(reads|follows|needs|meets|edits|searches))\b
```

| In place of | Write |
|---|---|
| "an opening", "an arrival", for one reading of a file | "each time an agent reads the file", "a run" |
| "hold", for what a file or a page has in it | "contain", "have", "say" |
| "the lack" | "what the reader lacks" |
| "the moment at which" | "when" |
| a file "behind" a row or a page | "the row names the file and says when to read it" |
| a thing that "only looks right" | "is accepted and still fails" |
| "stated from" | "based on" |
| "the send", "a landing", for a sentence that names the next file | "the row", "the sentence that names the file" |
| "a time" that reads or follows | "an agent that is editing", "when the agent searches" |

- Give the text to a reader who has not seen it, and ask what the text tells that reader to do. The answer is what you meant.

## Example

Good: one instruction.

```text
List a decision only when the note records it as settled. A choice that the note does not settle is an open question, or is left out: a decision that you infer, and that the note does not record, is a false record.
```

Nearest bad: the same instruction, as it is usually worded.

```text
Be laser-focused on real decisions. Don't let wishful thinking sneak into the list! IMPORTANT: make sure every decision is rock solid.
```

Clarity fails: "laser-focused", "sneak into" and "rock solid" are figures that the reader has to translate, and "real decisions" is never defined. Objectivity fails: "IMPORTANT: make sure" is emphasis, and a reviewer cannot check "rock solid". Eloquence fails: the three sentences do not follow from one another, and none gives a reason. Actionability fails: the reader is not told what to do with a choice that the note leaves open. The good version says what makes a decision listable, what becomes of the other choices, and why. Its reason lets the reader decide a case that the instruction does not name, such as a decision that one participant reports and the note does not confirm.

## References

| # | Page | File | Read | When | To |
|---|---|---|---|---|---|
| 1 | Scaffolding | [scaffolding](scaffolding.md) | when | deciding whether a text that you are about to write is covered by this page | take what an agent's scaffolding is |
| 2 | Single source of truth | [single source of truth](../principles/single-source-of-truth.md) | when | a sentence states a fact that another file owns | link the owner, and keep the two consistent |
