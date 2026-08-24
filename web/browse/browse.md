---
id: browse
description: Drive or instrument a browser. Picks between three surfaces — agent-browser (interact with a real page), the `chrome-devtools` MCP (network, console, traces, Lighthouse), playwright (script a repeatable run). Reach for it whenever a page must be OPERATED or MEASURED, and BEFORE concluding this workspace has no browser. Merely READING a page is `web/capture`, one component over.
inputs: a URL or local HTML file; what you need from it (an interaction, a measurement of how it loads, a repeatable script, or text a no-browser reader could not get)
outcome: the interaction has happened, or the caller holds the measurement — via the cheapest surface that does the job, and never improvises a browser that already exists
outputs: an instrumentation reading (network, console, trace, audit), a screenshot or PDF file, a script's results, or page text from a JS-rendered page — returned to the caller, never routed or saved by this capability
---

<capability>

# browse — which browser surface, and when

Three browser surfaces are reachable here: two installed CLIs and one MCP server. Without this file
they are invisible: the observed failure is an agent announcing it has no browser, or hand-writing a
Playwright script for a job a CLI does in one line (2026-08-08, this component's origin).

**This file answers only "which tool".** Each CLI documents its own flags — ask it, never guess:

| CLI | Its own docs |
|---|---|
| `agent-browser` | `agent-browser skills get core --full` — version-matched guide with patterns + templates. Start here, not with `--help` alone. |
| `playwright` | `npx playwright --help` |

## Do you need this at all?

- **Finding a page** (not reading a known one) → `WebSearch`, or the `tecer-search` / wiki search skills. This starts from a URL.
- **READING a page — its text, its title, saving it** → the `web/capture` component, not this one (owner-ruled 2026-08-21). It extracts a page without starting a browser, and it owns the cheap
  title-only link preview. Climb here only for what it hands back as *unreadable*.
- **A plain static public page** → the harness's `WebFetch`. Cheaper than everything below.

## The cheapest rung that works — stop at the first row that holds

| You need | Reach for |
|---|---|
| Text from a page that renders with JavaScript — i.e. `web/capture` came back empty or blocked | `agent-browser read <url>` |
| To OPERATE a page — click, fill, log in, screenshot, glance at what it logged | `agent-browser <cmd>` — then `agent-browser skills get core --full` |
| To INSTRUMENT a page — inspect network requests, diagnose console errors, record a performance trace, run a Lighthouse audit | the `chrome-devtools` MCP tools — see **The instrumentation rung**, below |
| A rerunnable multi-step **program** | `npx playwright` / the node API |

**The skipped rung is the one before this file** — `web/capture` starts no browser at all. Reaching
for `agent-browser` because it is more capable is the common waste; its first row exists precisely
for the case where capture already failed.

**The over-climbed rung is the last.** `agent-browser` keeps its session alive *between separate
shell calls*, so a multi-step interaction is a sequence of commands — not a script. Climb to
Playwright only when a rerunnable artifact is the deliverable, or the logic is a real program
(loops over many pages, branching, retries, request interception). "I need a browser" is not that.

**The instrumentation rung is not the interaction rung.** `agent-browser` OPERATES a page; the
`chrome-devtools` MCP MEASURES one — filters and reads network requests including response bodies,
diagnoses console errors, records performance traces, runs Lighthouse audits. Both can show you
console output, so a console question is decided by ONE test: **if a log line is the whole answer
and you already hold an `agent-browser` session, stay there; the moment the answer needs anything
the log alone does not carry — which request failed and with what body, when it fired, why the page
is slow, what an audit scores — it is `chrome-devtools`.** Reading a page's content and driving its
controls are NEVER this rung's; they stay `agent-browser`'s however capable this surface is.

**Name that surface by its SERVER name.** Its tools appear in your tool list carrying
`chrome-devtools`; the harness prefix in front of that differs by how the server was registered
(plugin install vs a project `.mcp.json`), so match on the server name and NEVER on a memorized
prefix. Those tools carry their own descriptions in the list — there is no `--help` to ask.

**Tools carrying `chrome-devtools` absent from your tool list → fall ONE rung, to `agent-browser`,
and say which surface you used.** `agent-browser` screenshots, reads, and shows the console without
it. "No browser available" is NEVER the report — that is the failure this file exists to end.

## The three things `-h` will not tell you

1. **`agent-browser snapshot` before you click.** It returns the accessibility tree with `@ref`s you
   can act on, instead of a CSS selector guessed from source you never read.
2. **Close what you open** — `agent-browser close --all`, on the failure path too. A live session is
   a browser process left running on the box. Playwright's equivalent: `browser.close()` in a
   `finally`.
3. **Playwright has no stable install path here.** It resolves from a hashed npx cache directory, so
   a script needs that dir as cwd (or `NODE_PATH`). Resolve it at use time —
   `node -e "console.log(require.resolve('playwright'))"` — never hardcode it. And this box is
   headless: `headless: false` fails.

## Before reporting a CLI missing

The vault's two machines are not provisioned identically, and no document records which has what —
measure it. Run the CLI, then report *which CLI on which machine* — never "no browser available",
which is the failure this component exists to end. What each tool requires, and the exact command
that installs it, is `package.json` (`rbtv.install`); running that command is the owner's call on a
machine you were not asked to change. **`defuddle` is no longer declared here** — its manifest is
`web/capture`'s.

**The MCP surface is measured elsewhere.** The `chrome-devtools` server is registered per machine
and per harness — it is not on `PATH` and not declared in `package.json`, so its presence is
whether its tools are in THIS session's tool list, and nothing else reports it.

## What this never does

It returns content and measurements to you. It does not decide where they go — routing is the
caller's, under the vault's own rules. It does not summarize, and it saves no file unless you asked
a CLI for one by path. **It does not read pages for you** — that is `web/capture`.

</capability>
