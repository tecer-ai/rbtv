---
id: capture
description: Read a web page and keep it. Fetches a URL, extracts clean prose through the strongest extractor present (defuddle → trafilatura → BeautifulSoup), tells a real article apart from a bot-wall or an empty JavaScript shell, and writes it where you point. Handles PDFs. Also the cheap title-only link preview. Reach for it BEFORE concluding this workspace cannot read a page.
# W6 — the CLIs this capability routes to (`exposes:` reference grammar).
exposes-cli:
  - capture-cli
inputs: a URL (or a local HTML/PDF/text file), and a destination — an exact file (`--out`) or a folder to name the file in (`--out-dir`)
outcome: the caller holds a readable capture of the page on disk, or a `blocked` verdict naming WHY it is not readable — never a file full of nav chrome, challenge-page text, or decoded PDF bytes
outputs: the saved file, an optional `.full.html` archival sidecar, an optional PDF text companion, and one JSON object on stdout (state, path, title, extractor used, prose length, failure reason)
---

<capability>

# capture — read a page, and keep it

`capabilities/capture/capture.py` — one CLI, JSON on stdout, exit 0 only when a page was actually
captured. **Ask it for its flags — `capture.py -h` — and never guess them.** This file carries only
what `-h` cannot: which extractor is right, and what a `blocked` result actually means.

    capture.py --url <url> --out-dir <dir>          # tool names the file: YYYY-MM-DD-<title-slug>.md
    capture.py --url <url> --out <file>             # exact path
    capture.py --file <path> --out <file>           # a local HTML/PDF/text file you already hold

## Do you need this at all?

- **Finding a page** (not reading a known one) → `WebSearch`, or the `tecer-search` / wiki search
  skills. This starts once a URL is known.
- **Just glancing at a plain, static, public page** → the harness's `WebFetch` is cheaper. Come here
  when you need the page ON DISK, when `WebFetch` failed, or when you need to KNOW whether what came
  back was the article or a wall.
- **Only "what is this link?"** → don't read the page at all. `references/link-preview.md`, one
  folder up, is the four-step chain that gets a title and description for almost nothing.
- **Operating or measuring a page** — clicking, logging in, screenshotting, reading network or
  console — → the sibling `web/browse` component. This one reads; that one drives.

## The extractor chain — which is best for what

`--extractor auto` (the default) tries the three in order and STOPS at the first whose prose clears
the rich-prose bar. Naming one explicitly runs ONLY that one, and an unavailable one is then a hard
error rather than a silent fall-through — which is exactly what you want when you are comparing.

| Rung | Best at | Weak at | Costs |
|---|---|---|---|
| `defuddle` | **The default answer.** Returns markdown with links, headings and lists intact, so a saved capture reads like the article rather than like a paragraph soup. Best when the capture will be READ by a person or re-rendered. | Sites with unusual DOM conventions; it is a single-strategy reader. | A node process. |
| `trafilatura` | **Recall.** The strongest boilerplate stripper of the three on odd layouts, paginated articles and non-English pages — it gets prose out of pages the other two give up on. Best when defuddle came back thin and you only need the WORDS. | Output is flatter: structure and links are largely gone. | A Python import, lazy. |
| `bs4` | **The last resort, and it earns it.** Renders every plausible content container AND `<body>`, keeps whichever yielded most text. Rescues a server-rendered page whose prose sits in a sibling of the semantic wrapper the other two trusted — the exact 2026-06-08 regression it was written for. | It is not smart. Expect some chrome to survive. | A Python import, lazy. |

**An absent rung is skipped, not fatal.** All three are optional (`../../package.json` § `rbtv.system`); the
ordering exists so a machine with only `defuddle` still captures. If a capture came out poor, the
first thing to check is which rung actually ran — the JSON's `extractor` field says.

## Reading the result — the four things `-h` will not tell you

1. **`state: blocked` is a MEASUREMENT, not a failure to retry.** It means the bytes that came back
   were not an article, and the `failure_reason` says which kind: below the byte floor (truncated or
   empty response), a captcha / bot-wall challenge phrase, or prose too thin — in absolute terms or
   against the body size — to be a page with content in it.
2. **Thin prose almost always means JS-rendered.** No extractor without a browser can read a page
   whose content arrives after the HTML does. That is the ONE legitimate climb into `web/browse`:
   `agent-browser read <url>`. Never report "the page has no content" from a blocked result — that
   measured the HTML, not the page.
3. **A bot-wall is not a bug to route around.** Report it. Retrying with a different user-agent to
   defeat a challenge is a decision the owner makes, not one this capability takes.
4. **A PDF is detected and handled, not decoded.** A URL that turns out to be a PDF is saved as a
   PDF — `--title` is REQUIRED for those (the filename is a title slug, no date prefix), an existing
   file of that name is never overwritten, and `--pdf-text` adds a pypdf text companion beside it.
   This exists because the alternative was silent: a PDF decoded as text, run through the HTML
   extractor, and written into a `.md` that passed every check with zero real prose in it.

## What this never does

It reads a page and puts it where you said. **It does not decide where that is** — routing a capture
into the vault is the caller's, under the vault's own rules, never invented here. It does not
summarize, does not follow links, does not crawl, and it holds no queue or index of what it has
captured: one call, one page, one file.

</capability>
