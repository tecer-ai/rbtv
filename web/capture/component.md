---
description: The capture component — reaching a page and KEEPING it. One first-party CLI fetches a URL, extracts it through the strongest of three extractors present, rules on whether what came back was an article at all, and writes it where the caller points. Handles PDFs; also owns the cheap title-only link preview. Driving or measuring a browser is the sibling `browse` component.
---

# capture

The `browse` component answers *how much of a browser does this need?* — and its first rung was
always the one that needed none: fetch the HTML, strip the chrome, hand back prose. That rung was a
single third-party CLI with a routing line, and it could not do the two things a real capture needs.

**It could not tell you when it had failed.** An extractor that returns nothing looks identical to a
page with nothing in it. The difference — JS-rendered, bot-walled, truncated, or genuinely empty —
is the difference between climbing one rung and reporting a wall, and no `--help` carries it.

**And it could not keep the result.** Everything downstream — a wiki ingest, a reading list, a
research sweep — needs the page ON DISK under a name it can find again, and every caller was
re-inventing that: a filename convention, a PDF branch, a check that the file was worth keeping.

This component is those two things, as one CLI. It is a port of the generic half of sb-os's
`wiki/scripts/sb-wiki-capture-source.py` (owner-ruled 2026-08-21) — a tool that had been doing this
job for months inside the wiki ingestor, mixed together with the wiki's own filing logic. The
filing logic stayed there; the fetching, extracting, judging and saving came here and lost every
wiki concept on the way (`raw/{origin}/` routing, the source-lifecycle queue, thesis slugs, the
staging-and-move machinery). The sb-os original is UNTOUCHED and still runs the wiki.

## Entry points

| Part | What it is |
|---|---|
| `capabilities/capture/capture.md` | The router capability. Which extractor is right, and what a `blocked` verdict means. The one exposed skill. |
| `capabilities/capture/capture.py` | The CLI it routes to. Self-documents through `-h`; inventoried in `exposure.csv` as this component's one first-party tool. |
| `references/link-preview.md` | The four-step chain for *what is this link?* — title and description, no page read. Applied, never executed. |

## The `defuddle` move (owner-ruled 2026-08-21)

`defuddle` was `web/browse`'s: its cheapest rung, and the first step of its link-preview chain. Both
came here in the same change, and browse's `package.json` no longer declares it.

The line the owner drew is **read vs. drive**. A component that reaches a page without a browser, and
a component that operates or measures one. The whole extractor question — defuddle first, trafilatura
when defuddle comes back thin, BeautifulSoup when both give up — is a reading concern end to end, and
it had no home in a browser router. Declaring `defuddle` in two `package.json`s to keep it in both
routers would have been two homes for one tool.

The consequence to hold: **an agent that wants to READ a page and lands in `browse` is one component
early.** Browse's own router says so in its § *Do you need this at all?*, and its ladder now starts
at a rung it does not own.

## The three extractors, and why the tool carries all of them

Owner ruling, same date: keep every extractor, chain them, and say which is best for what. They are
not redundant — they fail differently. `defuddle` returns structured markdown and is the right
answer almost always; `trafilatura` is the strongest at getting words out of odd, paginated or
non-English layouts and is what you reach for when defuddle came back thin; `bs4` is the dumb last
resort whose richest-container walk rescues a server-rendered page whose prose sits somewhere the
other two did not look. The comparison table is the router's (`capture.md`), where the agent
choosing between them reads.

⚠ **All three are OPTIONAL and lazily imported, and that is load-bearing.** The chain's order is
what lets a machine holding only `defuddle` still capture pages — which is the ignite VPS as
measured 2026-08-21 (`defuddle` present; `trafilatura`, `beautifulsoup4`, `pypdf` all absent). An
absent rung removes itself; it never breaks the tool.

## Dependencies — ONE manifest, one manager

`package.json` is this component's **dependency manifest** (`sd-graph show dependency-manifest`).
It declares `defuddle-cli` and the Node floor, and that is all npm resolves here.

**The three Python extractor libraries are NOT npm `dependencies`, and not a second manifest
either.** The record's rule is *one platform per component, never one per system*: a component picks
the package manager its dependencies actually belong to and uses only that one, because no tool
spans both ecosystems and the unifiers that would (Nix, mise) are ruled out for this system. So
`trafilatura`, `beautifulsoup4` and `pypdf` sit in `rbtv.system` — the map for host elements no
package manager the component uses can express, which the record's own schema names `python3` among
— each with its literal `pip3 install --user --break-system-packages` command, same
probe-and-report posture as `rbtv.install`.

⚠ **What the manifest cannot currently say: that those three are OPTIONAL.** npm's
`optionalDependencies` carries exactly that meaning ("the component degrades but still functions
without it") but only for elements the manager resolves, and `rbtv.system` has no required/optional
distinction at all. So the optionality is stated in the manifest's `description`, here, and in the
router — never in a field, because inventing one is what the stop rule forbids. It is a real gap in
the schema, surfaced rather than worked around.

That optionality is load-bearing: capture.py imports all three LAZILY, inside the function that
needs them, so an absent one removes a rung from the extractor chain rather than breaking the tool.
The chain's ORDER is what lets a machine holding only `defuddle` still capture pages — which is the
ignite VPS as measured 2026-08-21 (`defuddle` present; `trafilatura`, `beautifulsoup4`, `pypdf` all
absent, capture verified working).

⚠ The manifest is a DECLARATION, never a package. `"private": true`, no lockfile — every element it
declares is a BINARY that resolves to the workspace's shared bin root, so **a bare `npm install` in
this folder is a different act**, producing a `node_modules/.bin` that works but that no spawned
session sees. Provisioning a machine is the owner's call: report which rung was missing, never
install silently.

**There is deliberately no prose `dependencies.txt` beside the manifest.** One was written here and
deleted the same day, for the reason the record records as its own non-example: its install commands
had become a second copy of `rbtv.install` and `rbtv.system`, and its "measured on this box" table a
hand-maintained snapshot nothing refreshes. Measurement is a runtime act — run the check command —
never a stored table (`PRIN-11`). The single dated measurement above survives precisely because it
is dated.

## What this component is NOT

- **Not a search engine.** Finding the URL is `WebSearch` or the search skills. This starts from a URL.
- **Not a browser.** A page whose content arrives by JavaScript defeats every extractor here — that
  is the one legitimate climb into `web/browse` (`agent-browser read <url>`), and the router says so
  where the agent meets the blocked verdict.
- **Not a router or a writer of vault content.** It writes exactly where the caller points it. Where
  a capture BELONGS is the caller's routing decision under the vault's own rules — never invented here.
- **Not a crawler, a summarizer, or an index.** One call, one page, one file. It keeps no record of
  what it has captured; the wiki's queue stayed in the wiki, on purpose.
