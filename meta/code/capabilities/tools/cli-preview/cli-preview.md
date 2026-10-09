# cli-preview

Validates a Markdown-authored CLI output review and renders it to one
offline HTML file. Standard library only (Python 3.10+); no install step —
invoke by path from any working folder:

```
python <this-folder>/cli_preview.py init my-review/
python <this-folder>/cli_preview.py check my-review/
python <this-folder>/cli_preview.py build my-review/ --out my-review/preview.html
```

Not registered on `PATH` or as an rbtv component — source-invoked only.

## Folder contract

A review folder holds:

- `review.md` — exactly one, required. Exactly one `# Review: <title>`
  heading, a non-empty fixture description (fictional state screens rely
  on), and exactly one `## Command inventory` section listing every bare
  command path in scope (no flags) as `` - `command path` `` bullets — intro
  prose above the first bullet is fine, but nothing may follow the bullets
  except blank lines.
- Any other `*.md` file — screens, processed in filename order. Each screen
  is a `## <numeric id>. <title>` heading (id a positive integer) followed
  by fields and one fenced block (two for `Stream: both`). A literal
  `## heading`-looking line *inside* a fenced block is payload, not a new
  screen. Content before a file's first screen heading must be blank or a
  single `<!-- ... -->` comment.

Required fields per screen: `Category`, `Command` (backtick-wrapped in the
source; a paired outer backtick pair is stripped when stored), `Terminal
width` (positive integer), `Scenario`, `Exit code` (integer 0-255), and
`Command-path` (must match a `review.md` inventory entry — every screen
maps to a declared command, so nothing slips through undeclared). Optional:
`Help: yes|no` (marks the screen as that command's help screen — its
`Command` must then contain a literal `-h` or `--help` token, so a plain
success screen can never satisfy coverage by mislabeling; `check`/`build`
fail if any declared command has no `Help: yes` screen), `Stream:
stdout|stderr|both` (default `stdout`; `both` needs two fenced blocks
marked with a literal `Stdout:` / `Stderr:` line immediately above each,
stdout first — the two payloads stay separate in the rendered page, each
with its own copy button, never concatenated into one copyable blob; a
single-stream `stderr` screen is labeled "Stream: stderr" in its metadata).

Screen ids must be globally unique across all screens files and positive;
they do not need to be contiguous. A `` ```json `` fence must parse as
strict JSON — `NaN`/`Infinity`/`-Infinity` are rejected even though
Python's own `json.loads` accepts them by default.

`check` and `build` both run full validation and report every issue as
`file:line: message` plus a `fix:` line (or, with `--json`, as an
`issues` array of `{file, line, message, fix}`). `build` writes nothing on
a failed check. It refuses to overwrite an existing `--out` file without
`--force`, and refuses if `--out` would collide with one of the folder's
own `.md` inputs. The write is atomic (temp file + rename).

## What validation does NOT prove

Declared `Command-path` / `Help: yes` coverage only proves the review
*names* every command in its inventory and gives it a screen whose
`Command` contains a help token — it cannot prove the command inventory
itself is complete, that a screen's literal output actually matches what
the real command prints, or that help prose is accurate or complete. The
tool never inspects, imports, or executes the reviewed program; it only
reads Markdown text. Real-command and semantic verification is still the
author's and the informed reviewer's job (see the specification and
verification steps of the
[building-a-CLI method](../../methods/building-a-cli.md)).

## Reuse in this vault

`renderer.py` holds the HTML/CSS/JS shell (search, sidebar navigation,
copy buttons, mobile toggle) extracted from the original one-off
`rbtv-cli-ux` preview generator, with title, disclaimer, and screen data
as parameters. `contract.py` is the Markdown parser and validator for
*this* tool's folder contract (`review.md` + screens files, above) — it
has no role in the older, already-published `outputs.md` review, which
predates this contract and uses a different, simpler screen format
(numbered `## NN. Title` sections with no `review.md`, no command
inventory, no `Command-path`/`Help`/`Stream` fields).

`1-projects/rbtv-cli-ux/build/html-author/extract.py` keeps its own
regex parser for that older, hash-locked `outputs.md` fixture — it does
not call `contract.py`, and is not expected to, since the two formats
differ. `generate.py` in that same folder *does* call this tool's
`renderer.py` to render `extract.py`'s output, so the HTML/CSS/JS shell
has exactly one implementation; only the Markdown-to-screens parsing has
two, one per format, by necessity, not by drift. Neither script touches
the already-reviewed `outputs.md` or `preview.html`.
