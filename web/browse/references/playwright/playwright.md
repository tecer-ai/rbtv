# playwright-cli — command reference

> **Invoke it as `playwright cli <command>` — there is no `playwright-cli` on `PATH`.**
> This CLI ships inside the `playwright` package (`../../package.json` declares `playwright >=1.61`;
> measured 1.62.1 at `~/.local/bin/playwright` on the ignite VPS, 2026-08-31). Its own help prints
> the name `playwright-cli`, which is why every command below is written that way — read
> `playwright-cli open …` as `playwright cli open …`. Verify with `playwright cli --help`, and check
> the tool's bundled guide at
> `playwright/node_modules/playwright-core/lib/tools/skills/playwright-cli/SKILL.md` before trusting
> these files, which came from the retired `rbtv-studio` browser-automation workflow: every command
> family they document (route/unroute, tracing, video, storage state, run-code, sessions) is present
> in 1.62.1, but they are not version-tracked and the tool's own help is authoritative.
>
> **Open it as `playwright cli open --browser chromium <url>`.** Bare `open` targets a real Chrome
> install at `/opt/google/chrome/` that does not exist on the ignite VPS, and fails with
> `Chromium distribution 'chrome' is not found`. The working value `chromium` is NOT among those its
> own help lists; it resolves the bundled build under `~/.cache/ms-playwright/`. Every `open` example
> below omits this flag and will fail as written (measured 2026-08-31; the Windows desktop is
> unmeasured).
>
> **It writes into the working directory** — each snapshot lands in a `.playwright-cli/` folder
> beside wherever you ran it. Run it from a scratch directory, never from inside the vault.

## Screenshot hygiene — MANDATORY

Screenshots NEVER land in the vault. Always pass `--filename` with a path in the session's
scratchpad (or another directory outside the vault); never call `screenshot` bare, because its
default location is the working directory. Delete each file once you have read it, and sweep the
rest before the turn ends. No PARA folder is a screenshot destination.

## Gotchas

| Trap | Solution |
|------|----------|
| `file://` protocol blocked | Start a local server: `npx -y serve "/path" -l 3847 &` then `playwright-cli open "http://localhost:3847"` |
| Commands fail with "browser not open" | Run `playwright-cli open` or `playwright-cli open <url>` first |
| `navigate` is not a command | Use `goto` |
| Screenshot is blank/tiny | Use `--full-page` flag for full page captures |
| Need to wait for server to start | Run `npx serve` with `run_in_background: true`, wait for completion notification, then `open` |

## Essential workflow

```bash
# 1. Open browser (with optional URL)
playwright-cli open https://example.com

# 2. Navigate
playwright-cli goto https://example.com/page

# 3. Get page state (snapshot is the primary tool — returns element refs)
playwright-cli snapshot

# 4. Interact using refs from snapshot
playwright-cli click e15
playwright-cli fill e5 "user@example.com" --submit
playwright-cli type "search query"
playwright-cli press Enter
playwright-cli hover e4
playwright-cli select e9 "option-value"

# 5. Screenshots — ALWAYS pass --filename targeting the screenshots folder
playwright-cli screenshot --filename="$SCRATCH/view.png"
playwright-cli screenshot --full-page --filename="$SCRATCH/full.png"
playwright-cli screenshot e5 --filename="$SCRATCH/element.png"
# Delete each screenshot after analysis. Sweep the folder before turn end.

# 6. Scroll and inspect
playwright-cli eval "() => window.scrollTo(0, 1200)"
playwright-cli eval "document.title"
playwright-cli eval "el => el.textContent" e5

# 7. Navigation
playwright-cli go-back
playwright-cli go-forward
playwright-cli reload

# 8. Close
playwright-cli close
```

## Element targeting

Use refs from snapshots (preferred), CSS selectors, or Playwright locators:

```bash
playwright-cli click e15                                          # ref from snapshot
playwright-cli click "#main > button.submit"                      # CSS selector
playwright-cli click "getByRole('button', { name: 'Submit' })"   # role locator
playwright-cli click "getByTestId('submit-button')"               # test ID
```

## Keyboard and mouse

```bash
playwright-cli press Enter
playwright-cli press ArrowDown
playwright-cli mousemove 150 300
playwright-cli mousewheel 0 100        # scroll down 100px
```

## Tabs

```bash
playwright-cli tab-list
playwright-cli tab-new https://example.com/other
playwright-cli tab-select 0
playwright-cli tab-close 2
```

## Advanced capabilities

Read the reference file when needed — do NOT pre-load:

| Capability | File in this folder |
|------------|-----------|
| Full command catalog | `playwright-cli --help` |
| Playwright tests | `playwright-tests.md` |
| Request mocking | `request-mocking.md` |
| Running Playwright code | `running-code.md` |
| Browser sessions | `session-management.md` |
| Storage (cookies, localStorage) | `storage-state.md` |
| Test generation | `test-generation.md` |
| Tracing | `tracing.md` |
| Video recording | `video-recording.md` |
| Element attributes | `element-attributes.md` |
