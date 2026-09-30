---
name: web
description: "Use for web requests: read or save a page or PDF, preview a link, browse an interactive site, inspect browser behavior, or research sources with citations. Routes to the web module's capture, browse, and research parts."
---

# web

Route the request to one child. The unit `module/component#unit` is the file of that name in the component's unit folders (`rbtv install show <unit>` gives its path); open that file before using its tools. Resolve paths from the rbtv repository that contains this file.

| Request | Child |
|---|---|
| Read or save a web page or PDF; preview a link title | `web/capture#capture` — `capture-cli` |
| Interact with a page, inspect network or performance, or test browser behavior | `web/browse#browse` — agent-browser, Playwright, or Chrome DevTools as its router directs |
| Research a subject, judge sources, or provide citations | `web/research/references/standards.md`; use `web/capture#capture` for reading and `web/browse#browse` when a browser is needed |
