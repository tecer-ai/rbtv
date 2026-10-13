# Driving a browser

The result: a page operated, captured as an image or measured in a real browser, with every browser you started closed. Input: the URL, or the local file or running address of the app under review, and what the task needs from it.

Two programs do this work. `agent-browser` is the default: it operates and measures a page, one shell command per action, and keeps its session open between commands. `playwright cli` is used for the jobs in the table that `agent-browser` does not do. Each documents its own commands; read that guide before the first command and do not guess an option.

| Program | Its guide |
|---|---|
| `agent-browser` | `agent-browser skills get core --full` |
| `playwright cli` | `playwright cli --help`, whose first lines give the path of the guide installed with the program |

Choose a session name for the task and pass it on every command, including a single `read` or `screenshot`: `agent-browser --session <name> <command>`, or `playwright cli -s=<name> <command>`. A command without a name uses the session `default`, which every agent on the machine shares: another agent's command then acts on your page. The commands below are written without the name.

## Choose the command

| The task needs | Use |
|---|---|
| The text of a page whose content arrives by JavaScript | `agent-browser read <url>` |
| To operate a page: open, click, fill, log in, wait, read what it logged | `agent-browser open <url>`, then `agent-browser snapshot` and the action commands |
| An image of a page | `agent-browser screenshot <path>` |
| Network requests and a response body, a HAR file, a Chrome DevTools trace, an accessibility audit, Core Web Vitals | `agent-browser network requests`, `network request <id>`, `network har start` and `stop`, `trace start` and `stop`, `a11y --json`, `vitals --json` |
| Cookies, local storage, or a logged-in state to save and restore | `agent-browser cookies`, `storage local`, `state save` and `load` |
| A network response replaced or blocked | `playwright cli route <pattern>` and `unroute` |
| A video of the session | `playwright cli video-start` and `video-stop` |
| A Playwright file: a test, a trace for `playwright show-trace`, a generated locator | `playwright cli` |
| A program that runs again without you: loops over many pages, branches, retries | A script on the Playwright library |

Do not use `agent-browser` to replace or block a response, or to record video. In version 0.33, `agent-browser network route --abort` exits 0 and the request still completes, and `agent-browser record` needs `ffmpeg` installed separately.

The two programs write different trace files. `agent-browser trace stop` writes Chrome DevTools trace JSON, which the DevTools Performance panel and Perfetto open. A trace for `playwright show-trace` comes only from `playwright cli`. Choose by the viewer the reader will use.

A sequence of actions on one page is a sequence of `agent-browser` commands, not a script. Write a script only when the task asks for a program that runs again, or the logic loops, branches or retries.

## Operate a page

1. Open the page.
2. Run `snapshot` before the first click. It returns the page's elements with references such as `@e5`; act on those references, not on a selector guessed from the page source.
3. After an action that changes the page, take a new snapshot before the next action: the references belong to the snapshot that returned them.
4. Close your session, also when a step failed: `agent-browser --session <name> close`, or `playwright cli -s=<name> close`. Do not run `agent-browser close --all`: it closes the browsers of every agent on the machine.

Pass a path in your scratch folder to every command that writes a file (a screenshot, a trace, a HAR file, a video), unless the task names a destination. Run `playwright cli` from your scratch folder: it writes a `.playwright-cli/` folder in the folder it runs from.

## Review an app being built

Open the app the way its user will: start its server as the project documents and open that address, or open a built page with `agent-browser open file://<absolute path>`. `playwright cli` does not open `file://` addresses; serve the folder over HTTP first. For each screen the change affects, take a snapshot and a screenshot, read the screenshot, and read what the page logged with `console` and `errors`. Report what you saw against what the change was to do, with the screenshot paths. Stop any server you started.

## When a program does not start

| Message | Action |
|---|---|
| `agent-browser`: `No usable sandbox!` | Add `--args "--no-sandbox"` to the `open` command; the session keeps it for the commands that follow |
| `playwright cli open`: `Chromium distribution 'chrome' is not found` | Open with `playwright cli open --browser chromium <url>`. Its help does not list `chromium`; the value selects the browser installed by `playwright install chromium` |
| The command is not found | Report which program is missing on which machine, with the install command `rbtv doctor` prints for it. Run the install only when the user asked you to change the machine |

Do not report that no browser is available before running both programs. When one is missing, do the work with the other where the table allows and say which you used.
