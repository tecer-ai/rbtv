---
description: Read at the moment you need to know what a URL IS — its title and description — without paying to read the page. The four-step chain, cheapest first, and the stop rule.
tags: [web]
---

# Previewing a link without reading it

Identify what a URL is — title and description — without fetching, extracting, or saving its
content. This is applied, never executed: run the steps in order and **STOP at the first that
returns a title.**

Arrived here 2026-08-21 from `web/browse`, with `defuddle` (owner ruling: reading a page, in every
form including this cheapest one, is the `capture` component's).

1. **`defuddle`, one property at a time** — `defuddle parse <url> -p title`, then
   `defuddle parse <url> -p description`. No browser, no page body, no file written. This is the
   step that makes the other three rare.
2. **oEmbed, for a platform URL** — `WebFetch` against the endpoint that owns it:
   `https://publish.twitter.com/oembed?url=<url>` (Twitter/X) ·
   `https://www.youtube.com/oembed?url=<url>&format=json` (YouTube) ·
   `https://noembed.com/embed?url=<url>` (generic, for the rest). Each returns JSON carrying the
   title.
3. **`WebFetch` on the URL, meta-scoped** — prompt it with exactly: "Extract only the page title and
   meta description from the HTML head. Return title and description, nothing else." The scoping is
   what keeps this cheap; an unscoped `WebFetch` reads the whole page, which is the cost you came
   here to avoid.
4. **Ask the user** — report the domain and whatever the first three steps recovered, and request
   the title and description.

## The stop rule

**Needing the body means this was the wrong job.** Do not extend the chain to get content out of it —
go to `capabilities/capture/capture.md` and capture the page properly. This file's whole value is
that it is the thing you reach for INSTEAD of reading, and a preview that grows into a read is a
worse capture with none of the content gate's protections.
