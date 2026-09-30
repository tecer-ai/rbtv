# Template

The agent-readable shape of a standard file: what an agent reads and fills, such as an agent file's prompt sections or a skill's body. A template is a [cognitive unit](cognitive-unit.md). One file can follow both a template and a [schema](schema.md): an agent file's body follows its template and its frontmatter its schema, and a folder instructions file holds the installer's marked sections, which follow a template, beside the author's own text. Templates are kept in the `build` component's `templates/` folder, listed in its index file.
