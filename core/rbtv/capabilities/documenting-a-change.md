# Documenting a change

Keep rbtv's instructions and discovery routes accurate in the same change as its source. Start with the changed files and the behavior they add, alter or remove. Follow [the component's documentation rules](../CLAUDE.md) for current-design prose and standing decisions.

## Update what describes the change

Keep each changed file's name and description aligned with its purpose and use. Update the component or module record when that purpose changes, and the repository README when it describes the affected behavior.

Search current documentation for the affected names and behavior. When a field, file layout or operation changes, update its schema, glossary entry and inline template, capability guidance, framework route and standing decision wherever they describe the affected contract. Do not create another maintained explanation beside the owning page.

For a new file kind, folder convention, field or shared term, obtain the owner's agreement before building it. Then define the term before another file uses it. Keep authoring instructions in its entry, or a capability for a routed method; include an inline template for a fixed-layout authored file and a separate schema when software checks fields. Add a direct route from the appropriate entry point and record the decision and reason in `decisions.md`. If a required design choice is missing, raise it with the owner rather than writing a placeholder.

## Rename or remove

Update every current caller and dependent statement in the same change: glossary entries, capabilities, templates, schemas, framework routes, README, records and descriptions. Remove references to the retired name, record the decision, and check links from their final locations. Historical accounts retain their historical claims under the component's documentation rules.

For a renamed installed file, each affected installation adds it under the new name; follow [rbtv CLI](glossary/rbtv-cli.md) for installation and refresh operations.

## Verify before calling the change done

For changed scanned records, verify installer acceptance with `rbtv add` or `rbtv update scaffolding`, following rbtv CLI. For unscanned capability prose, follow the owning page's content and behavior checks; component installation does not validate it.

Search again for each changed name and the behavior it replaced. Confirm that current statements agree, required new terms have definitions, and links resolve. Raise inconsistencies outside the authorized change with the owner; do not silently widen the work to fix them.
