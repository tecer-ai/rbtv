# Reading a page

The result: the text of one web page, PDF or local HTML file, saved where the task says, with a statement of whether what came back was the article. Input: the URL or file, and the destination file or folder. When the task gives no destination, save in your scratch folder and report the path; this page does not choose a place in the workspace.

`page-capture` does the work without starting a browser. `page-capture -h` lists its options.

```
page-capture --url <url> --out-dir <folder>     # the tool names the file: YYYY-MM-DD-<title-slug>.md
page-capture --url <url> --out <file>           # an exact path
page-capture --file <path> --out <file>         # a local HTML, PDF or text file
```

It prints one JSON object and exits 0 only when `state` is `captured`. A blocked result whose `next` key is set names the command to run next.

## Read the result

| Result | What it means | What you do |
|---|---|---|
| `state: captured` | An article was extracted and written | Use the file. `extractor` names the extractor that produced it |
| `state: blocked`, `failure_reason` starts `low_content_density` | The HTML held too little text: the content arrives by JavaScript after the page loads | Read it with a browser: run the command in the result's `next` key, `agent-browser read <url>`, as [Driving a browser](driving-a-browser.md) describes. Do not report that the page has no content; the tool measured the HTML, not the rendered page |
| `state: blocked`, `failure_reason` starts `captcha_or_bot_wall` | The site refused the request | Report it. Do not retry with another user agent to pass the challenge; that decision is the user's |
| `state: blocked`, `failure_reason` starts `body_too_small` | The response was empty or cut short | Report it with the reason |

A URL that returns a PDF is saved as a PDF, not decoded into text. `--title` is required for it, because the file is named from the title; a file already at that name is never overwritten; `--pdf-text` writes a text copy beside it.

## Choose an extractor only when the default result is poor

The default, `--extractor auto`, tries three extractors in order and stops at the first that returns enough prose. An extractor that is not installed is skipped. Naming one runs only that one, and fails when it is not installed.

| Extractor | Use it when |
|---|---|
| `defuddle` | The default answer: Markdown with links, headings and lists kept |
| `trafilatura` | `defuddle` returned little: it extracts prose from unusual layouts, paginated articles and non-English pages, with the structure and links mostly lost |
| `bs4` | Both returned little on a page whose text is in the HTML: it keeps the largest text container, with some navigation text left in |

The tool reads one page per call. It does not follow links, summarize or keep a list of what it captured.
