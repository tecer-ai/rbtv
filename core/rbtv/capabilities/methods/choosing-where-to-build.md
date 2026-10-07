# Choosing where to build

Choose the module, component and repository or mirror location after [Choosing what to build](choosing-what-to-build.md) settles the file kind. A text edit does not by itself justify moving a file.

## Use the stated boundaries

When the user names a location, read that module's or component's full record description. Use the named place unless its boundary excludes the work. Another place also fitting is not a reason to reopen the choice.

Object when the named location excludes the work, puts installation-specific content in the shipped repository, duplicates an existing component's purpose, or creates a module without a second component that could belong there. State the concrete conflict and resolve it with the user before placing the file.

When no location is named, read module descriptions, then component descriptions within the matching module. Reuse the component whose purpose covers the work. A new file type or exposure method does not require a new component. Record the alternatives considered and the boundary that excluded them.

Read [Core](../glossary/core.md) or [Meta](../glossary/meta.md) when either is a candidate. Core is not a fallback for subject work that fits no current module. Work on how agents behave belongs to Meta according to its boundary, not to a subject module merely because its examples name that subject.

Create a component only when none in the matching module covers the work. Create a module only when no existing module covers it and you can name a second component that would belong there. Do not build that second component without a stated need.

## Repository or mirror

| Content | Location |
|---|---|
| Reusable by any user, without installation-specific values | `<module>/<component>/` in the repository |
| Personal workflow, installation values or experiment | `.rbtv/mirror/<module>/<component>/` |
| Self-contained skill package | `.rbtv/mirror/_skills/<name>/` only |

A [Mirror](../glossary/mirror.md) component with the same module and component name replaces the shipped component completely. The files are not merged. Use that name only for an intentional complete replacement, including files referenced by packs. A missing referenced file can prevent listing or installation. Give a personal addition its own component name instead of unintentionally hiding the shipped component.

A [Self-contained skill](../glossary/self-contained-skill.md) is not a component; the repository does not discover an `_skills/` directory.

## Write the boundary once

Use [Module](../glossary/module.md) and [Component](../glossary/component.md) for their records. The description's first sentence states the subject and nearest excluded work directly. Listings already show the module or component identifier; omit an introductory name label and commentary about unspecified future additions. Listing uses the first sentence, cut at 150 characters; keep the boundary within that span and do not put the exclusion after a period followed by a space.

Keep the record as the boundary's owner rather than creating a second definition. Use a noun for the folder name and existing glossary terminology. Do not create a glossary entry merely because a module was added.

## Review

Check the full record and the visible listing. Verify the named location against its actual boundary and inspect any same-name mirror replacement. Then ask a reader without the conversation to place another matching item and a neighboring excluded item from the description alone.

When scope changes, update the boundary in the same change. Outside folder names do not determine placement during conversion.
