# Template

A template is the layout of one file, written in the page that describes that file, as a code block that the builder fills. Outside rbtv a template is often a separate file, or a sample that is already filled. In rbtv it is not a file of its own, and it is not a finished file. A schema is a file that a program loads when it checks a record or frontmatter. The page "Schema"¹ says what a schema is. An example is one finished file, with its decisions already made. No page has an example.

A template is for the builder who writes that file from the page. An author wants one when the page describes one file that an author writes, and that file has a fixed layout. Write a template so that the builder fills each decision this file makes, and a second file of the same kind does not copy the first.

The page "Writing a glossary entry"² says how that part is written in an entry, and when the part is absent. A capability page has the same part when its work produces one file, and the file has a fixed layout. The page "Writing a capability"³ says when that part is present. A template is not a file, so this page has no layout of a file to copy. The page "Single source of truth"⁴ is why the layout is written once, in the page, and never in a second file.

The builder fills the template when it writes the file: each placeholder becomes the decision of that file, and no placeholder stays. The page "rbtv command"⁵ says what the program then accepts, which is a match of the fields against the schema and not of the body against the template.

A use: "The template of a rule has a placeholder for the point that the agent can check." A misuse: "Copy the template of the last rule, with its paths, and change the name."

## References

| # | Page | File | Read | When | To |
|---|---|---|---|---|---|
| 1 | Schema | [Schema](schema.md) | when | the file has a schema, or the layout is about to list fields | take what a schema is, so this layout does not become the file the program checks |
| 2 | Writing a glossary entry | [Writing a glossary entry](../writing-a-glossary-entry.md) | when | writing the part in an entry, or writing a placeholder | take how the part is written, when it is absent, and the form of a placeholder |
| 3 | Writing a capability | [Writing a capability](../writing-a-capability.md) | when | the page is a capability, not a glossary entry | take when that page has the part |
| 4 | Single source of truth | [Single source of truth](../principles/single-source-of-truth.md) | when | the layout is about to be written in a second file | keep one home, and link it |
| 5 | rbtv command | [rbtv command](rbtv-command.md) | when | asking the program to accept the built file | take what that acceptance shows, and that a schema match leaves the body unexamined |
