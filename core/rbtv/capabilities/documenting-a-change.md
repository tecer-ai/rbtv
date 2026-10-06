# Documenting a change

Use this after adding, changing, renaming, or removing anything in rbtv — a unit, a tool, a component, a module, a template or schema, or how a program behaves — and before calling the change done. It says which documents change with it, so the documentation never describes something that no longer exists and every new thing can be found. The documentation's own editing rules are in [`core/rbtv/CLAUDE.md`](../CLAUDE.md); among them, pages describe the design as it is now, and why it changed belongs only in [`decisions.md`](../decisions.md).

## 1. The unit describes itself

A unit's name and description, in its frontmatter or its JSON record, are what the [installer](glossary/rbtv-command.md) lists and what an agent reads before deciding to use it. Keep them saying what the unit is for and when to use it after every change. The installer checks them against the unit's [schema](glossary/schema.md): the change is not done until `rbtv install add` or `rbtv install update` accepts it.

## 2. Its records stay true

- When the change alters what a component or module is, update the description in its [`<component>.json`](glossary/component-json.md) or [`<module>.json`](glossary/module-json.md); those are what the installer lists.
- When the repository's README lists or describes what changed, update it.

## 3. A change to an existing kind

When the change alters how a kind of thing works — a field added to a frontmatter or record, a new section in a file, a program behaving differently — every page that describes it changes in the same commit: its schema and [template](glossary/template.md), its glossary entry, its guide, its line in [`rbtv.md`](../skills/framework.md), and its standing decision. Search the documentation for the thing's name to find every page that describes it.

## 4. A new kind of thing

A new kind — a file, folder, field, term, or unit that nothing defines yet, including one nobody foresaw — is a new convention. Get the owner's agreement before building it. Then, in the same change, write:

- its glossary entry, before any other file uses the new term;
- its guide, saying how to build it;
- its template, schema, or both, when its shape is fixed, listed in [`templates.md`](glossary/schema.md);
- one line in `rbtv.md`, where agents find it;
- the owner's decision and reason, in `decisions.md`.

When one of these cannot be written because its design is not decided, raise it with the owner. Never write a placeholder.

## 5. Removing or renaming

Remove or rename every mention in the same change: glossary, guides, templates and schemas, `rbtv.md`, the README, the records, and every unit or description that names it. A link to something that no longer exists is a defect. Record the decision. For a rename, each installation that had the unit adds it under its new name ([installer](../skills/framework.md)).

## 6. Done when

- the installer accepts the change;
- a search of the documentation for every changed name finds no page that contradicts it;
- every new term has its glossary entry;
- every inconsistency you found, even outside the change, has been raised with the owner.
