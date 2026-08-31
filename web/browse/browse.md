---
id: browse
description: "Drive or instrument a browser — routes to the cheapest surface that does the job. agent-browser drives AND measures a real page (interaction, network requests and response bodies, HAR, Chrome DevTools trace, cookies/storage state, accessibility, Core Web Vitals); playwright cli covers what it cannot — mocking a network response, recording video, and Playwright artifacts (codegen tests, show-trace traces, locators); the chrome-devtools MCP is the audit rung (Lighthouse, performance insights, heap snapshots, throttling). Reach for it before concluding this workspace has no browser. READING a page is web/capture, not here"
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

**The installed `playwright` package also carries an interactive CLI — `playwright cli <command>` —
that operates a live browser the way `agent-browser` does** (snapshot/click/fill, plus network
mocking, tracing, video, and storage state). `references/playwright/` documents it, indexed by
`references/playwright/playwright.md`; its own help is `playwright cli --help`. **Which of the two
interactive surfaces wins for a given job is NOT yet ruled** — until it is, `agent-browser` stays the
default this file routes to, and this CLI is reached deliberately for what the table above sends to
Playwright.

## Do you need this at all?

- **Finding a page** (not reading a known one) → `WebSearch`, or the `tecer-search` / wiki search skills. This starts from a URL.
- **READING a page — its text, its title, saving it** → the `web/capture` component, not this one (owner-ruled 2026-08-21). It extracts a page without starting a browser, and it owns the cheap
  title-only link preview. Climb here only for what it hands back as *unreadable*.
- **A plain static public page** → the harness's `WebFetch`. Cheaper than everything below.

## The cheapest rung that works — stop at the first row that holds

Every row below was measured on the ignite VPS on 2026-08-31, except where it says otherwise.
`agent-browser` both drives AND measures a page; it is the default, and the two rungs above it exist
for a short, specific remainder it cannot do.

| You need | Reach for |
|---|---|
| Text from a page that renders with JavaScript — i.e. `web/capture` came back empty or blocked | `agent-browser read <url>` |
| To OPERATE a page — click, fill, log in, screenshot, glance at what it logged | `agent-browser <cmd>` — then `agent-browser skills get core --full` |
| To MEASURE a page — list network requests and read a response body, capture a HAR, record a Chrome DevTools trace, audit accessibility, read Core Web Vitals | `agent-browser` too: `network requests` / `network request <id>` / `network har start\|stop` / `trace start\|stop` / `a11y --json` / `vitals --json` |
| Cookies, localStorage, or a saved logged-in state to restore later | `agent-browser cookies` / `storage local` / `state save\|load` |
| To MOCK or stub a network response, or to RECORD VIDEO | `playwright cli route <pattern> --status --body` / `unroute`, and `video-start` / `video-stop` — **not `agent-browser`**, see below |
| A Playwright ARTIFACT — a `.spec.ts` test, a Playwright-format trace for `show-trace`, a generated locator — or raw Playwright code | `playwright cli codegen` / `generate-locator` / `run-code`, or the node API |
| A Lighthouse audit, a performance trace analysed into insights, a heap snapshot, or CPU/network throttling | the `chrome-devtools` MCP tools — see **The audit rung**, below |
| A rerunnable multi-step **program** | `npx playwright` / the node API |

**The skipped rung is the one before this file** — `web/capture` starts no browser at all. Reaching
for `agent-browser` because it is more capable is the common waste; its first row exists precisely
for the case where capture already failed.

**Two jobs leave `agent-browser` for a measured reason, not a preference (2026-08-31).**
`agent-browser network route --abort` **exits 0 and does not block**: the targeted request still
fired with status 200 across three reloads and the resource still rendered. And `agent-browser
record start\|stop` fails outright — it shells out to `ffmpeg`, which is not installed on this box.
`playwright cli` does both: a `route` stub was verified returning the injected status, and
`video-start`/`video-stop` produced a real `.webm` using Playwright's own bundled ffmpeg. Do not
"try `agent-browser` first" for these two — it is known-broken here, and its zero exit code will
convince you it worked.

**The two tools' traces are different formats, so they are not interchangeable.** `agent-browser
trace stop` writes raw Chrome DevTools trace JSON (~10 MB for a short session, no extension), which
opens in the DevTools Performance panel, Perfetto, or `chrome://tracing`. Playwright's trace is a
different artifact and only `playwright cli` produces it, for `playwright show-trace`. Pick by which
viewer the reader will actually open.

**The over-climbed rung is the program rung.** `agent-browser` keeps its session alive *between
separate shell calls*, so a multi-step interaction is a sequence of commands — not a script. Both
CLIs also hold several concurrent named sessions (`--session <name>` / `-s <name>`), verified
independently addressable. Climb to the node API only when a rerunnable artifact is the deliverable,
or the logic is a real program (loops over many pages, branching, retries). "I need a browser" is
not that.

**The audit rung is what neither CLI has.** The `chrome-devtools` MCP owns Lighthouse audits,
turning a performance trace into named insights, heap snapshots, and CPU/network throttling — and
that is now its whole job here. It no longer owns network inspection or console reading: those were
measured working in `agent-browser`, one shell command each, and climbing to an MCP server for them
is the waste this ladder exists to stop. **Unlike every other row, this rung is UNVERIFIED** — its
tools were not exercised in the 2026-08-31 measurement, so treat a failure here as unmeasured
ground, not as impossible.

**Name that surface by its SERVER name.** Its tools appear in your tool list carrying
`chrome-devtools`; the harness prefix in front of that differs by how the server was registered
(plugin install vs a project `.mcp.json`), so match on the server name and NEVER on a memorized
prefix. Those tools carry their own descriptions in the list — there is no `--help` to ask.

**Tools carrying `chrome-devtools` absent from your tool list → fall to `agent-browser`, and say
which surface you used.** It screenshots, reads, shows the console, lists network requests, and
audits accessibility without that server. "No browser available" is NEVER the report — that is the
failure this file exists to end.

## The four things `-h` will not tell you

1. **`agent-browser snapshot` before you click.** It returns the accessibility tree with `@ref`s you
   can act on, instead of a CSS selector guessed from source you never read.
2. **Close what you open** — `agent-browser close --all`, on the failure path too. A live session is
   a browser process left running on the box. Playwright's equivalent: `browser.close()` in a
   `finally`.
3. **Neither CLI launches with its default flags on the ignite VPS — measured 2026-08-31.** Both
   work; each needs one flag that its own `--help` does not lead you to, and hitting the default is
   what produces the false "this box has no browser" report.

   | CLI | Bare command fails with | Launch it as |
   |---|---|---|
   | `agent-browser` | `No usable sandbox!` — the box has no usable Chrome sandbox | `agent-browser open <url> --args "--no-sandbox"` |
   | `playwright cli` | `Chromium distribution 'chrome' is not found at /opt/google/chrome/chrome` — it defaults to the real-Chrome channel, which is not installed | `playwright cli open --browser chromium <url>` — `chromium` is NOT among the values its help lists, but it is the one that works, resolving the bundled build in `~/.cache/ms-playwright/` |

   Measured on the ignite VPS only; the Windows desktop is unmeasured, so measure before assuming
   either flag is needed or sufficient there. Startup is ~1.2s for either once the flag is right.

4. **`playwright cli` writes into the working directory.** Each snapshot lands in a `.playwright-cli/`
   folder beside wherever you ran it — the vault `.gitignore` already carries that path (line 48),
   which is the trace of someone hitting this before. Run it from a scratch directory anyway.

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
