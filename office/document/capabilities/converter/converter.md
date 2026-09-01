---
id: converter
description: Export a markdown or HTML file to PDF or DOCX, in a branded or legal style. Purpose-independent — any consumer that already holds a finished document can invoke it, including the presentation capability's HTML deck.
exposes-cli:
  - converter-cli
inputs: a markdown or HTML file path; target format `pdf` | `docx`; style category `branded` | `legal`; an optional output path (`--out`)
outcome: a rendered PDF or DOCX file exists at the resolved output path, or the caller holds the full, unsuppressed error that stopped it — never a silently swallowed failure and never a half-written file left in place of a clear error
outputs: `{basename}.pdf` or `{basename}.docx` — a sibling of the input file (or the caller's `--out` path) with the input's basename and the target extension
---

<capability>

# converter — markdown/HTML to PDF or DOCX

Two engines, one purpose-independent capability: turn an authored markdown or HTML file into a
rendered document. `capabilities/converter/tool/md-to-docx.py` is the first-party DOCX engine —
**ask it for its flags (`md-to-docx.py -h`), never guess them.** PDF goes through the third-party
`md-to-pdf` CLI (npm; pulls Puppeteer/Chromium) — this file and `engines/reference.md`,
`engines/styling.md`, `engines/branding.md` carry what `md-to-pdf --help` does not.

## Do you need this at all?

This is the ONE rendering path for md/HTML → file in this module. `deck-production` prints its HTML
decks to PDF through this same path rather than standing up a second Chromium — see *HTML input*
below. If you only need to READ a page, this is not that; see `web/capture`.

## Inputs the caller resolves before invoking

1. **Target format** — `pdf` or `docx`.
2. **Style category** — `branded` or `legal`. Legal fits contracts, agreements, terms, NDAs, and any
   legal analysis; everything else (proposals, reports, plans, decks) is branded.
3. **Output path** — defaults to a sibling of the input: same directory, same basename, target
   extension. The caller may override with an explicit path. An existing file at that path is
   overwritten; this capability does not ask before overwriting.

## Style resolution — no search, no discovery

**Branded.** Style artifacts resolve by reading the FIXED workspace path `.rbtv/config/office/` —
never by scanning any workspace file to discover a brand folder's location. Expected there:
`document-style.yaml` (feeds the DOCX engine), `document-style.css` and `document-config.js` (feed
the PDF engine — read `engines/branding.md` for what `document-config.js` must set up: base64-encoded
logo, header/footer templates, margins that clear the header). **A missing brand pack is never a
parallel discovery scan** — it routes to the module's guided brand-pack setup, which is owned
elsewhere (the first capability that needs a pack triggers it); this capability's own job stops at
reading the fixed path and surfacing its absence.

**Legal.** Skip brand discovery entirely. Use the fixed, unbranded styles shipped beside this file:
`legal/legal-docx-style.yaml` (DOCX) and `legal/legal-pdf-style.css` (PDF) — conventions in
`legal/legal-style.md`. Never apply a brand-pack palette, logo, or header to legal output, regardless
of what the workspace's brand pack holds.

## Generate — PDF

```
md-to-pdf --launch-options '{"args":["--no-sandbox","--disable-setuid-sandbox"]}' --config-file .rbtv/config/office/document-config.js {input}
```
Legal:
```
md-to-pdf --launch-options '{"args":["--no-sandbox","--disable-setuid-sandbox"]}' --stylesheet capabilities/converter/legal/legal-pdf-style.css {input}
```
The `--launch-options` flag is REQUIRED — a caged/sandboxed seat runtime has no privilege for
Chromium's own SUID sandbox and Chrome crashes on launch without it (confirmed 2026-09-01); it is a
harmless no-op on an unsandboxed machine. Read `engines/reference.md` for the rest of the CLI flags
and gotchas (Windows EPERM/EBUSY, header font-size, `--stylesheet` replacing rather than extending
built-in CSS) before running.

**HTML input.** Markdown goes through Marked first, same as any `md-to-pdf` call. When the input is
already HTML — a rendered deck, a hand-authored page — **skip Marked and print the authored file
as-is**: pass the `.html` path to the same `md-to-pdf` command above. Marked passes full HTML
documents through unchanged (it does not re-parse tag soup as markdown), so the file prints exactly
as authored, through the same Puppeteer/Chromium engine, `printBackground` and page size intact. This
is why a second PDF engine is never built: any consumer that already holds finished HTML — including
`deck-production` — reaches PDF through this one path.

## Generate — DOCX

```
python3 capabilities/converter/tool/md-to-docx.py {input} {output} --style .rbtv/config/office/document-style.yaml
```
Legal:
```
python3 capabilities/converter/tool/md-to-docx.py {input} {output} --style capabilities/converter/legal/legal-docx-style.yaml
```
Requires `python-docx`, `pyyaml` (declared in this component's `package.json`). Pass
`--workspace-root` only when the style yaml's logo path is relative and must resolve against the
workspace root rather than the yaml's own folder.

## Errors

Surface the full error on any failure — a missing dependency, a malformed style file, a Chromium
launch failure. Never swallow an error, never substitute a default for a value the style contract
requires, and never retry silently.

</capability>
