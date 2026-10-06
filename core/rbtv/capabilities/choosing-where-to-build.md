# Choosing where to build

Choosing where to build is the decision of which module and which component the work goes in, and whether that home is in the rbtv repository or in the mirror. The page "Module"¹ and the page "Component"² say what those homes are. The page "mirror"³ says what the mirror is. It is not the decision of which kind of file carries the work: the page "Choosing what to build"⁴ makes that decision.

A folder the rbtv CLI accepts can still be the wrong home. The rbtv CLI finds a component by its record and reads the description. It does not compare that description with the files. An author reads this page when the work has no home yet: a new file, or an outside document to convert. Do not move a file to another module or another component because you were asked to change its text. Choose the home so that a later author, reading the description, puts the next file of the same work in and leaves a file of other work out.

## How it fails

The rbtv CLI can accept the folder, and the placement can still fail. It does not read whether the description covers the files.

- The user named a module or a component, and the file goes somewhere else because another home also fits. The named description does not exclude the work. The next conversation repeats the argument.
- A new module is created for one component, and no second component can be named. Later work in that area becomes another module, or other work is put in the one module. The rbtv CLI accepts a module with one component.
- A new component is created because the new file is a skill and the file already in that component is a command. Both serve one purpose. The next author looks in both folders.
- A personal file is written in the mirror under a shipped component's name, and the other files of that component are not copied. The rbtv CLI installs the mirror folder and does not install the shipped files. A pack that names a file of the shipped component cannot find it, and the rbtv CLI refuses. No component is listed or installed.
- The description lists what is inside and does not name what does not belong, or the exclusion sits after the first sentence. A list shows the first sentence, cut at 150 characters. The next author puts other work in.
- Work that is not rbtv's own operation, and not how agents behave, goes in core because no subject module was an exact match. The page "core"⁵ says that subject work belongs to its own module.
- How agents behave goes in a subject module because the work names that subject. The page "meta"⁶ says that this work belongs to meta.

## How to do it

1. **The next file a later author will misplace, then what the description has to decide.** Find the work that has no folder yet. A later author will read a description and decide whether the next file of the same work belongs with this one. The failure is that file in the wrong folder, or a file of other work left in, with the rbtv CLI still installing both. The cause is a description that does not name what belongs and what does not, or a folder chosen against a description that already names it. The situation is this work, before the first file is written, including when the user has named a module or a component. Write what the description has to decide: the next file of the same work in, a file of other work out.

2. **When the user named a module or a component, start from that name.** Read the description in the record file, `<module>/<module>.json` or `<module>/<component>/<component>.json`. Do not decide from a list line. A list keeps the text before the first period that is followed by a space, and cuts that text at 150 characters. When the name is core or meta, also read the page "core"⁵ or the page "meta"⁶. Those descriptions do not say what does not belong. Those pages say what does not belong. Use the named place unless that text excludes the work. Also object when the work has a path, an account, a host or a setting of one installation and the named place is the repository, or the reverse. When the named module or component does not exist yet, still start from that name. Object when an existing description already covers the work, or when a new module has no second component you can name. Do not object because another home also fits. State one objection, in the words of the description, and stop.

   Weak: "The user named office. Meta also fits a meeting summary, so ask to use meta."

   Strong: "The user named office. Its description does not exclude a meeting summary, so the file goes in office."

   The weak line opens a placement argument the description does not support.

3. **When the user named no place, use the existing component whose description covers the work.** Read each module description in its record file. Read each component description in the module whose description covers the work. For core and meta, read the pages "core"⁵ and "meta"⁶. Name each home you considered and the words that do not cover the work. A skill stays in the component whose description covers it, even when the file already in that component is a command. A different kind of file is not a new component. The kind is decided with the page "Choosing what to build"⁴.

4. **Create a component, or a module, only when no description covers the work.** Create a component in the module whose description covers the work, when no component's description does. Create a module only when no module's description covers the work, and you can name one further component that would belong there and that you are not building now. The rbtv CLI accepts a module with one component. Work that the page "meta"⁶ does not cover does not go in core for that reason. Read the page "core"⁵. The page "Keep it stupidly simple"⁷ refuses a new folder that this test does not require.

   Weak: "No component is named widgets, so create a module widgets for this one skill."

   Strong: "No module's description covers a widget catalog, and a second component, widget-reports, would belong there and is not built now. Create the module and this component."

   The weak line creates a module and names no second component.

5. **Choose the repository or the mirror.** Write in the repository, at `<module>/<component>/`, when any user could use the work and it has no path, account, host or setting of one installation. Write in the mirror, at `.rbtv/mirror/<module>/<component>/`, when the work is a personal workflow, a value of this installation, or an experiment. The page "mirror"³ says what that folder is. A self-contained skill, once the page "Choosing what to build"⁴ has given that kind, goes only at `.rbtv/mirror/_skills/<name>/`, as the page "Self-contained skill"⁸ says. The rbtv CLI discovers that folder only in the mirror. A copy in the repository is not listed. When the user named a module for that kind, say that the place is `.rbtv/mirror/_skills/`, because that folder is not a component.

   Weak: "Any user could use the workflow, so this installation's account id goes in the repository."

   Strong: "This installation's account id goes in the mirror. The workflow, with no account id, goes in the repository."

   The weak line puts a value of one installation in the repository because the workflow is general.

6. **A mirror folder that uses a shipped name replaces that component.** The rbtv CLI keeps the mirror folder and does not merge it with the shipped folder. After the repository changes, the mirror folder is still the one installed, on that same name. Use the shipped name only when you are replacing the component and the mirror folder has every file its users rely on, including every file a pack names. A file you leave out is not installed. A pack that names a file you left out makes the rbtv CLI refuse, and no component is listed or installed, until that file is in the mirror folder or the mirror folder is removed. A personal file that does not replace the shipped component gets a new component name in the mirror, in the module whose description covers it. To add a component the repository does not ship, use a name no shipped component has.

   Weak: "The personal skill does not replace document. Write it at `.rbtv/mirror/office/document/skills/`."

   Strong: "The personal skill does not replace document. Write it at `.rbtv/mirror/office/meeting-notes/`."

   The weak line uses the shipped name, so the rbtv CLI installs the mirror folder and does not install the shipped files.

7. **Write the boundary in the first sentence of the description.** When you create a module or a component, write the record as the page "`<module>.json`"⁹ or the page "`<component>.json`"¹⁰ says. Read the page "rbtv CLI"¹¹ for what the rbtv CLI refuses in that record. Put what belongs, and the nearest work that does not belong, in the first sentence of the description. A list keeps the text before the first period that is followed by a space, and cuts that text at 150 characters, so a second sentence is not in that line. Do not write the boundary in a second file. The page "Single source of truth"¹² says why a second copy drifts. Do not write a glossary page for a new module. Name the folder with a noun. The rbtv CLI stores that name as the id. A gerund is accepted and reads as an action. Check the name with the page "Terminology is king"¹³. Word the sentence as the page "Scaffolding language"¹⁴ says.

   Weak: "Daily knowledge work: narrative and documents. Not how agents behave."

   Strong: "Daily knowledge work: narrative and documents, not how agents behave and not the web."

   The weak line puts the exclusion after a period and a space, so a list shows only the first sentence.

- When you edit: a change to the text of a file that has a home does not move the file. When the scope of a module or a component changes, change the first sentence of its description in the same change.
- When you convert: the outside folder's name is not a module name. Place the files by the steps above. A workflow of one person goes in the mirror.
- When you review: quote the first sentence of the description and say whether it names what does not belong. Look for a mirror folder of the same module and component name. A review that only opens the new file misses a shipped component the mirror hid, and a boundary a list does not show.

Checks:

- The decision is the place the user named, unless that text excludes the work, the repository or the mirror is wrong for a value of one installation, an existing description already covers a new name, or a new module has no second component named. When the user named no place, or one of those four applies, the decision is an existing component, a new component in an existing module, or a new module for which one further component is named and not built.
- A new description's first sentence names what belongs and what does not. That sentence has at most 150 characters, and no period followed by a space before the exclusion.
- A mirror folder that uses a shipped name has every file a user of that component relies on, and every file a pack names. A personal addition that is not a replacement uses a new name.
- The rbtv CLI accepts the record. Acceptance shows that the record has the fields the rbtv CLI reads. It does not show that the description covers the work, or that a same-name mirror folder left a shipped file out.
- Place one further piece of work from the new description alone, with no conversation. It goes in when the first sentence covers it, and stays out when the first sentence excludes it.

## References

| # | Page | File | Read | When | To |
|---|---|---|---|---|---|
| 1 | Module | [Module](glossary/module.md) | when | naming a module, or creating one | take what a module is |
| 2 | Component | [Component](glossary/component.md) | when | naming a component, or creating one | take what a component is |
| 3 | mirror | [mirror](glossary/mirror.md) | when | the home is the mirror, or a same-name folder might replace a shipped component | take the folder |
| 4 | Choosing what to build | [Choosing what to build](choosing-what-to-build.md) | when | the kind of file is not yet decided, or the work may be a self-contained skill | decide the kind, and do not decide it here |
| 5 | core | [core](glossary/core.md) | when | the place is core, or no subject description covers the work | take what core excludes |
| 6 | meta | [meta](glossary/meta.md) | when | the place is meta, or the work is how agents behave | take what meta excludes |
| 7 | Keep it stupidly simple | [Keep it stupidly simple](principles/keep-it-stupidly-simple.md) | when | you are about to create a module or a component the description test does not require | take that a new folder is not justified by tidiness |
| 8 | Self-contained skill | [Self-contained skill](glossary/self-contained-skill.md) | when | the kind is a self-contained skill | take that `_skills/` exists only in the mirror |
| 9 | `<module>.json` | [`<module>.json`](glossary/module-json.md) | when | creating a module | write the record |
| 10 | `<component>.json` | [`<component>.json`](glossary/component-json.md) | when | creating a component | write the record |
| 11 | rbtv CLI | [rbtv CLI](glossary/rbtv-cli.md) | when | writing a record, or the rbtv CLI refuses one | take what the rbtv CLI refuses, and do not copy a refusal here |
| 12 | Single source of truth | [Single source of truth](principles/single-source-of-truth.md) | when | you are about to write the boundary in a second file | keep the description as the one boundary |
| 13 | Terminology is king | [Terminology is king](principles/terminology-is-king.md) | when | naming the folder | take that a name already in the glossary keeps that meaning |
| 14 | Scaffolding language | [Scaffolding language](glossary/scaffolding-language.md) | when | writing the description sentence | word that sentence |
