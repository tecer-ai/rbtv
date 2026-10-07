# Terminology is king

Use one term for one meaning, defined in one glossary entry. Use the whole term even when a shorter or more familiar word would be easier to write.

Apply this when naming a concept, folder, file or field, using an existing term, or changing its meaning. A second name can make an agent treat one thing as two; one name used for two meanings can make it combine things that behave differently.

## Find the term before using it

Search the glossary for the thing being named. Use the established term and its defined meaning, not automatically the word in the request. Write `cognitive unit`, not `unit`. Use ordinary words for other meanings rather than stretching a defined term.

A shared technical name needs an entry when separate files or a later task must use it with the same meaning. An ordinary word used locally or a search hint is not automatically a term. Do not create glossary entries for those. Follow [Scaffolding language](../glossary/scaffolding-language.md) for ordinary prose.

An rbtv term has its entry in the rbtv glossary. A component's subject-specific term belongs in that component's glossary. Do not redefine an rbtv term there. For a new shared term, write its entry under [Writing a glossary entry](../methods/writing-a-glossary-entry.md) before other files depend on it.

Use the term and route the reader to its entry instead of redefining it in each caller. The exception is [Single source of truth](single-source-of-truth.md): when the sentence cannot be understood without the definition, state it in the entry's exact words and link it.

## Names in files and changes

Use the rbtv term in source folder, file and field names. A harness's installed name is not a source convention: a command belongs in `commands/`, even when the installer writes it to Codex's `prompts/`. [rbtv CLI](../glossary/rbtv-cli.md) owns that mapping.

When a name or meaning changes, update its entry and all current files that rely on it in the same change. Search both the old spelling and statements of the old meaning. Do not leave aliases in instructions to bridge an unfinished migration. Historical records retain the words of the decision they record.

On conversion, map outside names to established terms or plain words. On review, compare the terms with their entries, check source names against installer conventions, and look for stale definitions. A page that links the right entry can still use the term in the wrong sense.
