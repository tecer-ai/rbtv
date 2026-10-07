# Capability

A capability is a source file containing a method or knowledge an agent reads when directed to it. It lives under `<module>/<component>/capabilities/`. The rbtv installer does not install or validate its prose.

Use a capability for work or reference material needed after an entry point or a prompt step selects it. Several callers may use the same page. Keep their shared instructions here rather than copying them into each caller.

## Write for the supplied inputs

Read the caller first. Identify what it already settled, what inputs it supplies and what work remains. Start the capability with that remaining result and required inputs; do not repeat the caller's selection instruction or describe when a harness should discover this page.

Use facts supplied by the route, facts this page owns and any sources the instructions explicitly authorize. Installation-specific paths, accounts and credentials come from task inputs or settings. If a required input is absent, stop and name what the caller must supply; do not search unrelated workspace files or invent a substitute.

Keep one purpose. A second independent result belongs in another capability; the caller should not make every reader pay for both. A step may link directly to another page when it needs that page's method. Do not replace the capability with an index of possible readings or route through another entry point.

Use [Cognitive unit](cognitive-unit.md) for shared instruction-writing requirements. For a method or knowledge page, use [Writing a capability](../methods/writing-a-capability.md). Specialized forms use their own guidance: [Writing a glossary entry](../methods/writing-a-glossary-entry.md), [Principle](principle.md), [Template](template.md) or [Schema](schema.md). A tool's executable is governed by [Tool](tool.md), not this page's prose layout.

A prompt's procedure describes the agent's overall work. A capability can perform one of its steps; it does not replace that procedure.

## Location and paths

Name the file for its work and place it by what it holds:

| Page | Location |
|---|---|
| A method page, which holds a procedure an agent follows | `<module>/<component>/capabilities/methods/` |
| A page that documents operating or maintaining a tool | With that tool, as [Tool](tool.md) specifies |
| A glossary entry, principle, template or schema | Its own folder: `glossary/`, `principles/` or `templates/` |

Supporting pages that only one method page routes to go in `methods/<name>/`, beside `methods/<name>.md`.

In a component of the `core` or `meta` module, `capabilities/` holds only these sub-folders: `glossary/`, `methods/`, `principles/` (`core/rbtv` only), `templates/` and `tools/`. Do not leave a page loose in `capabilities/`.

Do not place a capability under skills, rules or commands, and do not create `capabilities.md` or `glossary.md` as directory indexes.

Links inside the capability resolve from its own source folder. A skill or command links from its source file. A rule uses a repository-root or `.rbtv/` path for rbtv to resolve after placement. Follow [Prompt](prompt.md) for prompt links and [Folder instructions](folder-instructions.md) for links from installed folder guidance.

A workspace file reached through folder instructions may instead be a [Folder artifact](folder-artifact.md). Supporting resources distributed inside a [Self-contained skill](self-contained-skill.md) remain inside that skill's folder.

## Changes and tests

Edit the source; its next reading receives the change. Update any caller whose description, condition or inputs no longer match. When converting supporting material from an outside skill, preserve its requirements but remove repeated selection instructions and installation-specific assumptions. Use [Choosing what to build](../methods/choosing-what-to-build.md) for content of another kind.

Test the capability through its caller, without supplying facts the caller never provides. Use a second route or a second task, plus a missing-input case. Check that the agent completes the remaining work, follows the missing-input instruction and reads only authorized sources. Installing the component is not a test of this page.
