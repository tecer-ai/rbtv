---
name: Browser Automation
description: Automate browser interactions, take screenshots, test web pages with Playwright CLI.
---

# Browser Automation with playwright-cli

## Screenshot Hygiene — MANDATORY

All screenshots MUST be written to `.claude/skills/rbtv-playwright-cli/screenshots/` (vault-relative). NEVER let screenshots land in the vault root, the working directory, or any PARA folder.

| Step | Requirement |
|------|-------------|
| 1. Create folder | Before the first screenshot in a session, ensure the folder exists. |
| 2. Use `--filename` | Always pass `--filename=".claude/skills/rbtv-playwright-cli/screenshots/<name>.png"`. NEVER call `screenshot` without `--filename`. |
| 3. Delete after use | When you finish using a screenshot (analysis complete, task done), delete the file. Before ending the turn, delete every screenshot you created this session. |

Rationale: the default screenshot location pollutes the vault. The screenshots folder is gitignored and ephemeral.

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
playwright-cli screenshot --filename=".claude/skills/rbtv-playwright-cli/screenshots/view.png"
playwright-cli screenshot --full-page --filename=".claude/skills/rbtv-playwright-cli/screenshots/full.png"
playwright-cli screenshot e5 --filename=".claude/skills/rbtv-playwright-cli/screenshots/element.png"
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

| Capability | Reference |
|------------|-----------|
| Full command catalog | `playwright-cli --help` |
| Playwright tests | `{rbtv_path}/workflows/browser-automation/data/references/playwright-tests.md` |
| Request mocking | `{rbtv_path}/workflows/browser-automation/data/references/request-mocking.md` |
| Running Playwright code | `{rbtv_path}/workflows/browser-automation/data/references/running-code.md` |
| Browser sessions | `{rbtv_path}/workflows/browser-automation/data/references/session-management.md` |
| Storage (cookies, localStorage) | `{rbtv_path}/workflows/browser-automation/data/references/storage-state.md` |
| Test generation | `{rbtv_path}/workflows/browser-automation/data/references/test-generation.md` |
| Tracing | `{rbtv_path}/workflows/browser-automation/data/references/tracing.md` |
| Video recording | `{rbtv_path}/workflows/browser-automation/data/references/video-recording.md` |
| Element attributes | `{rbtv_path}/workflows/browser-automation/data/references/element-attributes.md` |
