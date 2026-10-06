# Writing a capability

Write the method or knowledge an agent needs after a route sends it to this page. Follow [Capability](glossary/capability.md) for its location, inputs and relationship to the caller. Use [Writing a glossary entry](writing-a-glossary-entry.md) for a page that defines a term; use [Principle](glossary/principle.md), [Template](glossary/template.md) or [Schema](glossary/schema.md) for those forms.

## Establish what the reader receives

Read the caller and identify the work already completed, inputs supplied and result still needed. Record the decisions this page must teach and failures found in existing work or tests. Do not make the reader repeat the caller's selection or your authoring research.

A reusable page must work from the inputs its routes supply. State the required inputs and the action on a missing input. Keep installation-specific paths and accounts in the task or settings, not in shipped guidance.

## Write the remaining work

Start with the result and required inputs. Write steps in the order the agent performs them. For a knowledge-only page, organize facts by their use; do not number facts as actions.

Use headings for the work itself. Add a separate failure section only for consequences not already explained beside the relevant instructions. Name the files produced when their structure is part of the work. Include a template only when the result is one file with a fixed layout; do not insert a template of the capability page itself.

Apply [Scaffolding language](glossary/scaffolding-language.md) for reasons and examples. Follow the framework's principles for defaults, conditional decisions and shared ownership; do not copy their rules into this page. Keep the decisions specific to this work and route to shared instructions where needed.

When several routes use the page, retain only the work they need in common. A step may read another capability when its condition is met; it must name that page directly, not send the agent to a directory index. Keep the current page responsible for doing its work rather than becoming another list of links.

## Test through the routes

Give a fresh agent a realistic task and the caller. Make the capability available when the caller directs the agent to read it. Supply the expected inputs without revealing the answer. Test another route as well, or another task through the same route when only one route exists.

Check the produced result, missing-input behavior and any unexpected reading or repeated work. Add a mode-specific test when editing, conversion or review has a distinct failure. A component's installation does not test this page: rbtv does not install or validate capability prose.

Keep the input and output evidence. Investigate a failure before attributing it to the page; correct an identified guidance defect and rerun with a fresh agent. Do not apply the six-run installable-file test merely because this is a Markdown file.

When editing, update callers whose descriptions or inputs changed. When converting outside supporting material, preserve its requirements while removing duplicated selection instructions and installation-specific assumptions. Supporting files of a self-contained skill remain in that skill's folder. Record removed or moved requirements in the change evidence.
