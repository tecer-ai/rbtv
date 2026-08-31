---
description: The browse component — the workspace's three BROWSER surfaces (two CLIs and one MCP server), reached through one skill. Drive a real page, script one, or instrument one; nothing here summarizes, routes, or saves. Reading a page without a browser is the sibling `capture` component.
---

# browse

Web-research CLIs live on this workspace's machines. Until this component existed every one of them
was reachable only by an agent who happened to open `.artifacts/capabilities.md` and read the right
row — so the common outcome was an agent concluding "I have no browser" and improvising, or
hand-rolling a Playwright `node -e` script that an installed CLI already does in one line (observed
2026-08-08, this component's origin).

This component makes them **entry points** rather than trivia: one skill routes across three
surfaces (`agent-browser`, `playwright`, and the `chrome-devtools` MCP server), and the routing
question is always the same one — *how much of a browser does this actually need?*

**It answers that question for a browser only.** Reading a page — clean text, a title, a saved file —
left this component on 2026-08-21 with `defuddle`, to the sibling `capture` component (see § *The
`defuddle` move*, below). The first rung of the ladder is now one component over.

## The routing question — cheapest rung that works

| You need | Reach for | Why not the next one down |
|---|---|---|
| The readable text of a page — article, doc, reference | the sibling `capture` component | No browser process at all. Not this component's at all since 2026-08-21. |
| To interact with a page — click, fill, log in, screenshot, read the console | `agent-browser` | A real browser, driven one command at a time, session persisting between calls. Built for exactly this caller. |
| To measure a page — network requests and response bodies, HAR, a Chrome DevTools trace, accessibility, Core Web Vitals | `agent-browser` as well | Measured working 2026-08-31, one shell command each. This row used to send the caller to the MCP server; it no longer does, because climbing there for a request list is the waste this table exists to prevent. |
| To mock a network response, or record video | `playwright cli` | `agent-browser`'s own equivalents are broken on this box and fail SILENTLY — `network route --abort` exits 0 without blocking, and video needs an `ffmpeg` that is not installed. |
| A Playwright artifact — a `codegen` test, a `show-trace` trace, a locator — or raw Playwright code | `playwright cli`, or the node API | These exist in no other surface here. `agent-browser`'s trace is Chrome DevTools JSON, a different artifact for a different viewer. |
| A Lighthouse audit, performance-trace insights, a heap snapshot, CPU/network throttling | the `chrome-devtools` MCP tools | The audit rung, and now its whole job. Not an installed CLI — it is registered, so it is present in a session as MCP tools or not at all. UNVERIFIED on this box. |
| To script a repeatable multi-step run, or anything above cannot express | `playwright` node API | Only when a *program* is the deliverable. Writing a script for a job `agent-browser` does in one command is the failure this table exists to prevent. |

A page that renders its content with JavaScript defeats every no-browser reader — that is the one
legitimate reason to climb from `capture` into this component for pure reading
(`agent-browser read <url>`).

## One capability, one router — and no file per CLI (owner-ruled 2026-08-08)

The obvious shape was a capability folder per CLI. **It was built that way and deleted the same
day.** Each file had become a worse copy of `agent-browser skills get core --full` and
`npx playwright --help` — restating a flag surface that ships with the binary, version-matched, and
drifts the moment either side moves.

So this component is ONE capability: `browse.md`, the router. It answers *which
tool*, plus the handful of things `-h` does not say (sessions persist and must be closed; Playwright
has no stable path here). Everything else is the CLI's own to document.

**Adding a further third-party CLI is a row in `browse.md`'s table — not a new file, and not an
`exposure.csv` row** (see that file's header for why).

**And the router stays at the component root, not in a `capabilities/` folder.** That is the ruled
shape for a component holding ONE capability that carries no tool and no sub-structure
(`meta/planning/references/kind-capability.md` § *where that file lives*, which cites this very file
as its live example). A `capabilities/` folder is EARNED by a second capability or a first tool;
this component has neither and is not to pre-build one. The sibling `capture` component does have a
tool, which is why its file sits at `capabilities/capture/capture.md` — the same rule, the other branch.

**A `plugin/MCP` registration is the ruled exception, and it DOES take a manifest row.** An MCP
server is a part of its own kind, carried by the `config` exposure method: one row whose
`entry-point` names a harness-agnostic server-declaration file in this component, which
materialization then realizes per harness (`decisions.md#d-exposure-part-kind-plugin-mcp` +
`#d-mcp-registration-is-config`, owner-ruled 2026-08-15). That is what the `chrome-devtools` row and
`mcp.json` are — a registration, not a fourth capability file.

## The `defuddle` move (owner-ruled 2026-08-21)

`defuddle` was this component's first rung and its cheapest: clean text with no browser process, and
the title-only link preview built on `defuddle parse -p title`. It is now the sibling `capture`
component's — declaration (`package.json`), routing, and the link-preview chain all moved there in
one change, and this component's `package.json` no longer names it.

The split the owner drew is **read vs. drive**: a component that reaches a page without a browser,
and a component that operates or measures one. Capture's extractor chain (`defuddle` →
`trafilatura` → BeautifulSoup) is a reading concern end to end and had no home here; keeping
`defuddle` in two routers would have been two homes for one tool.

The consequence to hold: this component's ladder no longer starts at its own first rung. An agent
that arrives here to *read* a page is one component early, and the router says so in its own
§ *Do you need this at all?*.

## The `playwright-cli` reference set (moved in 2026-08-31, owner-ruled)

`references/playwright/` holds ten files documenting the interactive CLI that ships inside the
`playwright` package — reached as `playwright cli <command>`, never as a `playwright-cli` binary,
which does not exist on `PATH`. Its own help prints the name `playwright-cli`, which is why the
files are written that way. Measured against 1.62.1 (`~/.local/bin/playwright`, ignite VPS,
2026-08-31): every command family the files document — route/unroute, tracing, video, storage state,
run-code, sessions — is present. The tool also ships its own guide at
`playwright/node_modules/playwright-core/lib/tools/skills/playwright-cli/SKILL.md`, which is
authoritative where the two disagree; these files are not version-tracked against it.

They were staged in the build-ignite backlog under a folder already named for this component,
orphaned when the `rbtv-studio` browser-automation workflow they belonged to was retired; their own
text still pointed at `{rbtv_path}/studio/workflows/browser-automation/data/references/`, a path
that no longer exists.

They are **reference material, so they carry no `exposure.csv` row** — a `references/` file is wired
in only by being pointed at from the routing body, exactly as `web/capture` does with
`references/link-preview.md` and `core/coding` does with its four discipline files. `browse.md`
carries that pointer.

The set's index is `references/playwright/playwright.md`. It arrived as `workflow.md` carrying skill
frontmatter — a second router that would have competed with `browse.md`. The frontmatter is stripped
and the file is a plain index; **it must never be re-exposed as a skill**, because this component's
settled shape is one capability and one router (§ *One capability, one router*, above).

**The routing question this set raised — RULED (owner, 2026-08-31), option (a), by deliverable.**
`playwright cli` operates a live page the way `agent-browser` does, so this component reaches two
interactive surfaces with overlapping jobs. The ladder in `browse.md` was rewritten off measurement
rather than off the help text, and the split is now:

- **`agent-browser` drives AND measures** — it is the default. Verified working here: network request
  listing and response bodies, HAR capture, Chrome DevTools tracing, cookies/localStorage/state
  save-restore, accessibility audit, Core Web Vitals, concurrent named sessions.
- **`playwright cli` owns a short remainder** — mocking a network response and recording video (both
  because `agent-browser`'s equivalents are broken on this box, below), plus Playwright artifacts
  (`codegen` tests, `show-trace` traces, `generate-locator`) and raw Playwright code.
- **The `chrome-devtools` MCP dropped to an audit rung** — Lighthouse, performance-trace insights,
  heap snapshots, throttling. It lost network inspection and console reading to `agent-browser`,
  which does both in one shell command. This rung is UNVERIFIED and `browse.md` says so.

**Two measured defects drive that split, and both are silent.** `agent-browser network route
--abort` exits 0 without blocking anything — the request still fired at status 200 across three
reloads. `agent-browser record start|stop` fails because `ffmpeg` is absent on this box. The
equivalent `playwright cli` commands were verified working (a stub returned the injected status; a
real `.webm` was produced from Playwright's bundled ffmpeg).

**Both CLIs also need an undocumented launch flag here**, which is the true cause of every historical
"this box has no browser" report: `agent-browser` needs `--args "--no-sandbox"`, and `playwright cli`
needs `--browser chromium` (a value its own help does not list — it otherwise targets a real Chrome
install that is absent). `browse.md` § *The four things `-h` will not tell you* carries both.

All of the above was measured on the ignite VPS on 2026-08-31. **The Windows desktop is unmeasured**
— the flags, the two defects, and the `ffmpeg` absence may all differ there.

Not moved with them: `screenshot-capture` (a Python program that builds a design exemplar set). It
uses a browser but its job is design reference, not browsing, so it went to the design side of the
backlog for a separate ruling.

## Dependencies

`package.json` is this component's **dependency manifest** (`sd-graph show dependency-manifest`,
minted 2026-08-08 by `decisions.md#d-dependency-manifest`): what the environment must provide,
declared in npm's own manifest rather than a format rbtv coins, read by `rbtv install`.

⚠ It is a DECLARATION, never a package. `"private": true`, no lockfile, and `rbtv install` resolves
these to the workspace's shared bin root so the binaries land on `PATH` — **a bare `npm install` in
this folder is a different act**, producing a `node_modules/.bin` that works but that no spawned
session sees.

**There is deliberately no companion doc of measured per-machine state.** One existed and was
deleted the same day: its install recipe had become a second copy of the `rbtv.install` commands,
and its per-machine table was a hand-maintained snapshot that goes stale in silence. Measurement is
a runtime act — run the element's install command's own probe, or `rbtv install` when it reads
manifests — never a stored table (`PRIN-11`).

⚠ **Measured 2026-08-08 on the ignite VPS: `playwright` does not satisfy this manifest.** It resolves
only from a hashed npx cache directory, so nothing outside that directory can `require` it — the
declaration says the environment provides it and the environment does not, really. `agent-browser` is correctly in
`~/.local/bin` (`defuddle` is `capture`'s manifest to measure now). The fix is the declared command
(`rbtv.install.playwright`); it has not been run, because provisioning is the owner's call.
The Windows desktop is UNMEASURED.

## What this component is NOT

- **Not a search engine.** Finding the URL is the harness's `WebSearch` or the `tecer-search` /
  `sb-wiki-search` skills. This component starts once a URL is known.
- **Not a router or a writer.** It returns page content to the calling agent. Where that content
  lands is the caller's routing decision, governed by the vault's own rules — never invented here.
- **Not a replacement for `WebFetch`.** For a plain, static, public page the harness's own fetch is
  cheaper than every capability below. Climb into this component when that has failed or clearly
  will.

## Placement — CLOSED: this component lives under the `web/` module (owner-ruled 2026-08-10)

From 2026-08-08 this component sat FLAT at `.rbtv/mirror/browse/` — at module depth, with no module
tier above it — by owner ruling, after the module/component/flat alternatives were shown. That
revision recorded the consequence as a prediction: *"any reader that walks
`mirror/<module>/<component>/` will not find this component… this folder either moves under a module
or that reader learns both depths."*

**The reader arrived, and the prediction was exact.** A seat's prompt-card `exposes:` declaration
resolves references by segment count — `part` = own component · `component/part` = sibling component,
same module · `module/component/part` = another module's component — all anchored at
`<tree>/<module>/<component>/` (`materialize-seats.py` `resolve_seat_exposes`). **No reference of any
length could name a component sitting at module depth**, so no seat could be given this skill at all.
The owner chose the move: `.rbtv/mirror/web/browse/`, under a new `web/` module.

The KG membership tests still read component-hood for this folder — one skill, one interface, one
function — and that is what it remains. The tension the move creates is the MODULE's, not this
component's: `web/` today groups one component where the test asks for ≥2. It is recorded in
`../module.md` rather than resolved, and the registry settles it (`PRIN-10`).
