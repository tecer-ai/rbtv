# Module

A module is a folder of components that share one subject. The folder sits at the root of the rbtv repository, or at the root of the mirror, and it has a record that the program reads when it lists the folder. Outside rbtv a module is a package of code. Here the folder is not a package, and the program does not read a package file as the record.

A module keeps the components of one subject together, so a later author can tell whether the next component belongs there. An author wants one when the page "Choosing where to build"¹ has given this subject a new module. Write a module so that a later author, reading the first sentence of the description, puts the next component of this subject in and leaves a component of a neighboring subject out.

## How it fails

The program can accept a module, and a later author can still place the next component in the wrong folder. The program reads the description and does not compare it with the components.

- The first sentence names what is inside, or it allows work of any subject to be added later. It does not name the nearest subject that does not belong. A later author puts a component of that subject in.
- The first sentence names the components that exist today. A component of the same subject that is not in the list looks like a new module, so the later author creates another module, or adds the new work to a component that the sentence already names.
- The exclusion sits after `. `, or the piece before that split is longer than 150 characters. A list shows the cut piece. The later author who reads the list never sees the exclusion.
- The folder name is a gerund, or it is a glossary term in another sense. A later author looks for a subject and finds an action, or finds the other term.
- The folder has an index file, or the boundary is only in `decisions.md` or in a glossary page. A later author follows that file. The description and the file stop agreeing. The program does not read the index.
- The folder has the record and no component folder. The module does not appear in a list. A later author cannot find the subject.

## What it is composed of

The author writes the folder `<module>/`. The page "Choosing where to build"¹ decides the repository or the mirror.

The folder always has the record `<module>.json`, named after the folder. The program reads the description from that file. A list shows one piece of the description. The page "`<module>.json`"³ says how to write the record. This page does not list its fields. The author decides the first sentence of the description. A later author places the next component from that sentence.

The folder has at least one component folder. The page "Component"² defines a component. This page does not say which files a component contains. The page "rbtv command"⁴ says what the program refuses when the record is missing, and what the scan does with a folder that has no component.

The folder may have `decisions.md`. That file records decisions. It is not the boundary.

The folder has no index file. Do not write `capabilities.md`, `principles.md`, `glossary.md`, or a file whose only job is to list the components. The program does not read those files.

## How to build it

1. **The next component that a later author will misplace, then the purpose.** The page "Choosing where to build"¹ has already said this subject needs a module. Find the component that a later author will place next, and the nearest component that must stay out. The failure is the next component in another module, or the neighboring component in this one. The cause, for a module, is a first sentence that does not name the subject, or does not name the nearest subject that must stay out. The other cause is a folder name that reads as an action. The situation is this subject, before the folder is written, including when the user has named the module. Write the purpose from that failure: a later author, reading the first sentence, puts the next component in and leaves the neighboring component out.

   Weak: "A later author puts the next component of a widget catalog in."

   Strong: "A later author puts the next component of the widget catalog in, and leaves out the component that produces the documents in which the catalog is sent."

   The weak line names no component that must stay out, so the sentence written from it has no exclusion.

2. **Name the folder with a noun for the subject.** The program stores the folder name as the id. A list shows that name, and every component's identifier starts with it. The record has no second name. Choose a noun for the subject, not a gerund for an action, because a gerund is stored the same way and reads as something the module does. The page "Terminology is king"⁵ says how to check the name against the glossary.

   Weak: `planning`

   Strong: `plan`

   The weak line is stored as the id, so a later author looks for a subject and finds an action.

3. **Write the boundary as the first sentence of the description.** Write that sentence before the record. It names the subject, and the nearest subject that does not belong, in one sentence. Do not name the component folders: a component that does not exist yet has to pass the same sentence. Do not repeat the folder name: a list already shows the id, and those words take the place of the exclusion. The page "Choosing where to build"¹ says what a list shows of that sentence, so the exclusion has to be in the first piece. The page "Single source of truth"⁶ refuses a copy of the sentence in `decisions.md`, in a glossary page, or in any other file. Write the sentence in the wording of the page "Scaffolding language"⁷. When the module is core or meta, read the page "core"⁸ or the page "meta"⁹ before you change the sentence. Those pages name the work that stays out. The descriptions do not name that work. Do not add a page of that kind for another module.

   Weak: "The catalog component and the reports component, not the documents those reports are sent as."

   Strong: "A catalog of widgets and the reports drawn from that catalog, not the documents those reports are sent as."

   The weak line names two components, so a third component of the same subject looks excluded, and the later author creates another module for it.

4. **Write the record and the first component in the same change.** Write `<module>/<module>.json` as the page "`<module>.json`"³ says, with the sentence from the previous step as the description. Write the first component in the same change, as the page "Component"² says. Do not write `capabilities.md`, `principles.md`, `glossary.md`, or a file that lists the components. A later author who opens one follows a list the sentence does not control. When the folder has `decisions.md`, keep the boundary in the description.

- When you edit: a change to a component's text does not by itself change the sentence. When the subject of the module changes, change the first sentence in the same change, because a later author places the next component from that sentence. When you rename the folder, rename the record to the same name in the same change, and change every current file that starts an identifier with the old name. The program reads the record that is named after the folder.
- When you convert: do not keep an outside folder's name when it is a gerund or a term in another sense, and do not copy its list of packages into the description. Write the name and the sentence by the steps above. Place the files with the page "Choosing where to build"¹.
- When you review: quote the first sentence and say whether a later author can put the next component in and leave the neighboring subject out. The folder name is a noun. The sentence does not name component folders. The exclusion is in the piece that a list shows. The folder has the record, at least one component, and no index file. A review that only lists the components misses a sentence that does not decide the next one.

Checks:

- A reviewer sees a noun as the folder name. The record's first sentence names the subject and the nearest subject that must stay out. The exclusion is in the piece that a list shows. The sentence does not name component folders and does not repeat the folder name. The folder has at least one component and no index file. The boundary is not in a second file.
- The program accepts the record. Acceptance shows that, when a component folder is present, the record was read and the module is listed; a folder with the record and no component is skipped unread. It does not show that the sentence decides the next component. The page "rbtv command"⁴ says what a refusal shows, and what the scan does with a folder that has no component.
- Give a later author the first sentence only, and two components, one of this subject and one of the neighboring subject. The first goes in. The second stays out.

## References

| # | Page | File | Read | When | To |
|---|---|---|---|---|---|
| 1 | Choosing where to build | [Choosing where to build](../choosing-where-to-build.md) | when | deciding whether this subject needs a new module, placing files on a convert, or choosing the repository or the mirror | take that decision, and do not take the wording of the sentence |
| 2 | Component | [Component](component.md) | when | writing the first component, or naming what a module contains | take what a component is, and do not take how a module's sentence is written |
| 3 | `<module>.json` | [`<module>.json`](module-json.md) | when | writing the record | write the record, and do not take a list of fields from this page |
| 4 | rbtv command | [rbtv command](rbtv-command.md) | when | the record is missing, a folder has no component, or a run refuses the module | take what the program refuses and what it skips |
| 5 | Terminology is king | [Terminology is king](../principles/terminology-is-king.md) | when | naming the folder | take that a name already in the glossary keeps that meaning |
| 6 | Single source of truth | [Single source of truth](../principles/single-source-of-truth.md) | when | about to write the boundary in a second file | keep the first sentence as the one boundary |
| 7 | Scaffolding language | [Scaffolding language](scaffolding-language.md) | when | writing the first sentence | word that sentence |
| 8 | core | [core](core.md) | when | the module is core | take the work that stays out, which the description does not name |
| 9 | meta | [meta](meta.md) | when | the module is meta | take the work that stays out, which the description does not name |
