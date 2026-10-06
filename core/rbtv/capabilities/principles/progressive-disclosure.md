# Progressive disclosure

Give an agent each instruction when the work needs it. Keep later methods out of earlier readings, and make the route to them available before they are needed.

Early content adds context load; missing content creates a context gap. [Context window](../glossary/context-window.md) defines those problems. First decide whether the content is needed under [Keep it stupidly simple](keep-it-stupidly-simple.md), and where its authoritative home belongs under [Single source of truth](single-source-of-truth.md). This principle decides when the agent reads it.

## Place by an observable condition

Name the task condition or completed result that makes the content necessary. If that condition is unknown, settle it before placing the content. Keep in the current body only what every reading of that body needs. Put a case-specific method in the capability that case opens, and name its load condition in the route. Use [Entry point](../glossary/entry-point.md) and [Routing table](../glossary/routing-table.md) for the body and row.

A route must distinguish a nearby case that should not load the page. Use `DO NOT LOAD WHEN` in descriptions and wherever the table row needs that exclusion. A filename alone does not tell the reader whether to open it.

Split work into phase files when the later method is unnecessary during the earlier phase and its start can be recognized without reading the earlier method. A later agent must be able to resume from that phase's file and supplied state. Do not split solely by length or call headings separate phases while every reading still loads all of them.

## Use the existing forms

- Several capabilities sharing a purpose or source documents may belong under one exposure method. Follow [Nested exposure](../nested-exposure.md); do not automatically create one skill per page.
- Text that must already be present when a condition can arise on any task belongs in a [rule](../glossary/rule.md). Its condition determines when the agent acts. Route a conditional method from it rather than pasting the whole method into every task.
- For content supplied by entering a folder, follow [Folder instructions](../glossary/folder-instructions.md). Existing workspace records are [folder artifacts](../glossary/folder-artifact.md), not missing indexes.

Do not add `capabilities.md`, `glossary.md` or `principles.md` to list a source folder. The entry point routes directly to the needed page. Supporting files of a self-contained mirror skill follow the exception in [Capability](../glossary/capability.md).

## Review the reading path

On edit, test whether a new sentence is needed on every reading of its body. If an identifiable case does not need it, move it to that case's page or route. On conversion, replace an all-phase checklist with the actual reading paths; preserve required inputs at each transition.

When changing this principle, give an agent a task for a later phase and the entry point: it should select that phase without reading other phases' methods. Give another agent the phase file and its required inputs: it should be able to resume. Installer acceptance cannot prove either result and does not install capability pages.
