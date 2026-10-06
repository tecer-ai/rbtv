# Principle

A principle states a design choice that a builder applies before writing a file. Its first sentence must let a reviewer accept or reject a design; naming a desirable quality is not enough.

Use a principle when the same unsettled choice applies to more than one kind of file and no existing mandatory page already decides it. A task-time instruction belongs elsewhere. Follow [Choosing what to build](../choosing-what-to-build.md) if the content does not meet this boundary.

## Write the design test

Name two kinds of design affected by the choice and a concrete failure the choice prevents in each. If the second kind cannot be named, the content is probably a method for one kind. If an existing principle already decides it, update that home rather than creating another mandatory reading.

Open with the choice in plain language, followed by the case where it still applies despite a competing convenience. Explain what the builder must inspect and what design would fail. Avoid slogans such as “prefer quality” and the form “X, even over Y.” The builder should not need to invent the acceptance criterion.

Use [Writing a glossary entry](../writing-a-glossary-entry.md) for the principle's presentation. Its failures and checks concern designs, not a running agent's next task step. Require a section, field or file only when the design choice itself requires one. Do not add structure just to demonstrate compliance, repeat another principle or invent a local tie-break between principles; [Keep it stupidly simple](../principles/keep-it-stupidly-simple.md) owns that decision.

## Place and route it

Write one Markdown file without frontmatter in `core/rbtv/capabilities/principles/<name>.md`, using a lowercase hyphenated name. Add a direct link to the mandatory readings in the [framework skill](../../skills/framework.md), before its conditional table. Name the test and result; this reading has no exclusion. Do not add `principles.md`.

The mandatory-reading instruction supplies the loading decision. The principle does not need its own description or instructions about when to open it. Links resolve from this source folder: neighboring principles use their filenames and glossary entries use `../glossary/`.

## Edit, convert and review

Edit the source and update the framework reading instruction when its stated test changes. The next reading uses the source directly. When converting an outside principle, retain the actual design choice and necessary reasoning, turn implications into observable design checks, and route task-time orders to their proper kind. Do not preserve headings or explanations that add no decision. One occurrence captured from a conversation is not yet a general principle; [Tips development](../tips-development.md) governs that capture.

Test with two kinds of design that violate the choice. The builder should identify and correct both without adding an unnecessary section or task-time order. Also confirm that framework actually routes to the page. Installer acceptance of the component does not review the principle or load it for a builder.
