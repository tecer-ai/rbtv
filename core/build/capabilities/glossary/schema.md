# Schema

The code-readable shape of a standard file, or of what programs read in it, such as a file's frontmatter: which fields it has, which are required, and what each may hold. A program checks a file against its schema and refuses a file that does not match. A schema is written as a JSON Schema, `<name>.schema.json`, and kept beside the templates in the `build` component's `templates/` folder. A file both agents and programs read follows a [template](template.md) for what agents read and a schema for what programs read; the schema is the authority for the fields.
