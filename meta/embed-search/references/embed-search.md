---
description: "Use to search markdown in a local folder by meaning, keyword, or substring, or inspect and refresh its search index."
exposes-cli:
  - voyage-embed
---

# embed-search

Run `voyage-embed query --root <folder> "<question>"` to rank markdown
sections. The query refreshes
the index; use `index --root <folder>` to refresh it without a query and
`status --root <folder>` to inspect it. Run `voyage-embed --help` for flags
and read `meta/embed-search/component.md` for the ranking and fallback behavior.
