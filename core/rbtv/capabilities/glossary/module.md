# Module

A module is a folder grouping components of one subject. It sits at the repository root or mirror root and contains `<module>.json` plus at least one component folder.

Use [Choosing where to build](../choosing-where-to-build.md) before adding a module. It owns the placement decision and the requirement to identify a second component that could belong to the subject without building it speculatively.

## Name and boundary

Use a noun for the subject, not an action or a glossary term with a different meaning. The folder name is the module identifier and prefixes its components' identifiers; the record has no separate module name.

Describe the subject shared by the module's components without naming individual components. Its first sentence names the subject and the nearest excluded subject. Follow Choosing where to build for the listing's 150-character first-sentence limit.

The record is the boundary's owner. Do not duplicate it in an index, a glossary entry or `decisions.md`. For Core or Meta, read their existing glossary entries before changing their boundaries; do not create such a page for every new module.

## Build and update

Write the module record using [module-json.schema.json](../templates/module-json.schema.json) and the first [Component](component.md) in the same change. A folder containing only the record and no component is skipped by discovery. Use [rbtv CLI](rbtv-cli.md) for validation behavior.

Do not add a file whose sole purpose is listing components. A decisions file is optional and records actual standing decisions, not another boundary definition.

Changing a component's wording does not by itself change the module. Update the description when the subject changes. For a rename, change the folder, record filename and every current identifier using the old prefix together. On conversion, do not inherit an outside package list or unsuitable folder name as the boundary.

## Verify

Give a reader the first sentence and two possible components: one matching the subject and one from the nearest excluded subject. The reader should place only the first in the module. Verify discovery with the record and a component present.
