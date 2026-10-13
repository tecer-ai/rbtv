# page-capture

`page-capture` fetches one URL, or takes one local HTML, PDF or text file, extracts the article as Markdown and writes it to the file or folder its arguments name. [Reading a page](../../methods/reading-a-page.md) is the method that runs it and says what to do with each result. `page-capture -h` is the interface reference.

## What a run returns

One JSON object on standard output, with every key present on success and on failure, and exit status 0 only when `state` is `captured` or, with `--title-only`, `titled`.

| Key | Holds |
|---|---|
| `state` | `captured`, `titled` (a `--title-only` run that found a title) or `blocked` |
| `url` or `file` | The source given |
| `path`, `sidecar` | The file written and, when the mode keeps the raw page, the `.full.html` file beside it |
| `title`, `description` | The title, and the description the page's meta tags declare; a `--title-only` run fills both from the page's head |
| `extractor`, `mode` | The extractor that produced the text, the output mode |
| `bytes`, `prose_chars` | Size of the fetched body and of the extracted text |
| `failure_reason` | Why the run was blocked: `body_too_small`, `captcha_or_bot_wall` or `low_content_density`, followed by the measured values; `no_title` for a `--title-only` run; or the fetch error |
| `next` | The command to run next, when one can still get the page: `agent-browser read <url>` after `low_content_density`. Otherwise null |
| `transform_error`, `transform_warning` | A failure or warning of the PDF text copy |

The tool fetches once and runs every check and extractor on those bytes. It writes only where `--out` or `--out-dir` says and keeps no state.

## Maintenance

The program is one file, `capture.py`, on the Python 3 standard library. Its module docstring states the order of the extractors and of the content checks, with the false result each ordering prevents; read it before changing either. The thresholds are the constants near the top of the file (`_BODY_MIN_BYTES`, `_PROSE_MIN_CHARS`, `_DENSITY_MIN_RATIO`, `_PROSE_OK_CHARS`).

Every extractor is optional, and the program skips one that is absent. The component record, `browse.json`, holds each one's install command, and `rbtv doctor` prints it for those that are missing.

| Extractor | Software |
|---|---|
| `defuddle` | The `defuddle` command of the npm package `defuddle`, on Node 20 or later |
| `trafilatura` | Python package `trafilatura` |
| `bs4` | Python package `beautifulsoup4` |
| PDF text copy | Python package `pypdf` |

Run the checks with `python3 test_capture.py` from this folder; they use no network. After a change to an option, the help or the result, follow [Building a command-line interface](../../../../code/capabilities/methods/building-a-cli.md) and [Tool](../../../../../core/rbtv/capabilities/glossary/tool.md).
