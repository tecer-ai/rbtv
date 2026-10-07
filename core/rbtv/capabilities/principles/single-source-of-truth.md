# Single source of truth

Each fact, instruction, setting and operation has one home where it is maintained. Other files point to that home, even when copying the content would save their reader a lookup.

Apply this before adding content and whenever a change affects something another file states. Two maintained copies can disagree after either changes; an agent reading one cannot infer which was intended.

## Choose and use the home

Search for the existing statement, including in other components. Search by meaning, not just the word being used. When it exists, link it. When it does not, place it with the facts that change for the same reason, in the file the author must change when that behavior changes. The file currently open is not a reason to choose it.

For glossary entries, [Writing a glossary entry](../methods/writing-a-glossary-entry.md) assigns ownership. [rbtv CLI](../glossary/rbtv-cli.md) owns how the installer is run and what it recognizes or enforces. A type-specific instruction may name a field or an installer fact needed to make that instruction executable; it must not reproduce the owning field list or installation reference.

Default to a link. If the current sentence cannot be understood without stating the fact, use the home's exact words and link it. Keep that dependent statement aligned whenever the home changes. Do not change the home merely to justify a conflicting restatement. [Terminology is king](terminology-is-king.md) governs the term and its meaning; [Scaffolding language](../glossary/scaffolding-language.md) governs the sentence.

When two files need the same method, give it one home and route both readers there. Follow [Cognitive unit](../glossary/cognitive-unit.md) for shared instructions and [Choosing what to build](../methods/choosing-what-to-build.md) when the kind is unsettled. Multiple routes may lead to one capability.

## Operations, state and generated text

Give an operation one implementation. Human and agent interfaces call it, keeping only their own interface-specific checks. [Agent parity](agent-parity.md) governs how both reach it.

Keep each kind of state in one authoritative source. Views read that source; do not maintain a parallel list by hand. Change the source of generated text and regenerate it. The generated portion is overwritten on the next run; independently authored text elsewhere in the same file is a different case.

## Change and review

When changing a fact, update its home and every current dependent statement that would disagree in the same change. Links need no copied-fact update. When converting outside material, assign each part to its home before placing it.

Review across files: select a changed fact, open its home and the files that state it, and compare them. Confirm that operations share their implementation, state views read their source and generated portions were not hand-edited.
