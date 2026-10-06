# Documenting a change

Use this after adding, changing, renaming, or removing anything in rbtv — a file, a tool, a component, a module, a template or schema, or how a CLI behaves — and before calling the change done. It says which documents change with it, so the documentation never describes something that no longer exists and every new thing can be found. The documentation's own editing rules are in [`core/rbtv/CLAUDE.md`](../CLAUDE.md); among them, pages describe the design as it is now, and why it changed belongs only in [`decisions.md`](../decisions.md).

## 1. The file describes itself

A file's name and description, in its frontmatter or its JSON record, are what the [installer](glossary/rbtv-cli.md) lists and what an agent reads before deciding to use it. Keep them saying what the file is for and when to use it after every change. For a scanned file, the installer checks its record against its [schema](glossary/schema.md); verify acceptance with `rbtv add` or `rbtv update scaffolding`. For unscanned capability prose, verify its instructions, links and result through the owning page; component acceptance does not validate that prose.

## 2. Its records stay true

- When the change alters what a component or module is, update the description in its [`<component>.json`](templates/component-json.schema.json) or [`<module>.json`](templates/module-json.schema.json); those are what the installer lists.
- When the repository's README lists or describes what changed, update it.

## 3. A change to an existing kind

When the change alters how a kind of thing works — a field added to a frontmatter or record, a new section in a file, a CLI behaving differently — every page that describes it changes in the same commit: its schema, glossary entry (including any inline [template](glossary/template.md)), capability guidance, route in [framework](../skills/framework.md), and standing decision. Search the documentation for the thing's name to find every page that describes it.

## 4. A new kind of thing

A new file kind, folder convention, field or term that nothing defines yet is a new convention. Get the owner's agreement before building it. Then, in the same change, write:

- its glossary entry, before any other file uses the new term;
- the authoring instructions in that entry, or a capability when the work is a routed method;
- its inline template when the author writes a fixed-layout file, and a separate schema when software validates its fields;
- a direct route in the appropriate entry point, so agents can find it;
- the owner's decision and reason, in `decisions.md`.

When one of these cannot be written because its design is not decided, raise it with the owner. Never write a placeholder.

## 5. Removing or renaming

Remove or rename every mention in the same change: glossary, capabilities, inline templates and schemas, framework routes, the README, the records, and every file or description that names it. A link to something that no longer exists is a defect. Record the decision. For a rename, each installation that had the file adds it under its new name ([installer](glossary/rbtv-cli.md)).

## 6. Done when

- the installer accepts changed scanned records, and changed prose passes the checks of its owning page;
- a search of the documentation for every changed name finds no page that contradicts it;
- every new term has its glossary entry;
- every inconsistency you found, even outside the change, has been raised with the owner.
