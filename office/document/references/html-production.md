---
description: "Read at the moment an agent is about to write HTML itself — the four file-mechanics rules that bind agent-authored HTML only."
tags: [document]
---

# html-production — file mechanics

Binds agent-authored HTML only. Learning does not bind this file; its mechanics are builder-owned.

These four rules are applied against the HTML file the agent writes. They carry no look, no typeface, no colour, and no page-type profile.

## 1. Static markup only

This is what makes hypresent (the comment-review tool these pages open in) able to anchor comments.

All content is written directly as static markup. Never build content at load time by appending DOM nodes from data. hypresent freezes rendered nodes into the saved file and the page's script re-adds them on reopen, so content shows twice.

Anything commentable must be a real, durable node that already exists in the markup. Scripts that add interactivity to content already present (filtering, show/hide, jump links) are encouraged.

**Failure test:** content that appears only after a script runs cannot take a comment and is a fail.

## 2. Heavy assets external

Binaries — images, screenshots, and other heavy files — go in a sibling folder named `{html-filename-without-extension}-assets/`, referenced by relative path. One folder per html, named after that html. Example: `report.html` → `report-assets/`.

Inline only tiny vector or CSS bits. Base64 ONLY when a true single self-contained file is explicitly required.

**Failure test:** a binary embedded as base64 without that explicit requirement, or an assets folder that does not match the html filename, is a fail.

## 3. The agent note

The FIRST node inside `<body>` is a non-rendered HTML comment telling a later agent not to read the file whole and naming the structure as the map:

```
<!-- AGENT NOTE: do NOT read this file whole. Structure = the <nav> jump-links and the section id anchors — grep those to map it, then read only the range you need. Heavy assets live in the sibling -assets/ folder. To edit, anchor on the nearest section id or heading. -->
```

The page MUST make that note true: real section `id`s, a `<nav>`, predictable headings.

**Failure test:** a missing AGENT NOTE, or a note the page's actual structure does not match, is a fail.

## 4. Source-sync

When the html renders another file, write or update a minimal `CLAUDE.md` in the output folder recording that source and html are a synced pair — an edit to one updates the other in the same change.

Keep that file minimal. If one already exists, add the sync rule without disturbing the rest.

**Failure test:** an html that renders a source file with no synced-pair record, or an edit that updates only one side of the pair, is a fail.
