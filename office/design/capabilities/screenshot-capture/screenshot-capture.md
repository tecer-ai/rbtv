---
description: capture curated exemplar screenshots of reference sites into a project's reference set, with a manifest row per capture
inputs: one or more target URLs (--url, repeatable); a reference-set path containing an exemplars/ folder (--refs); optional viewport WxH (--viewport, default 1440x900); optional CSS selector for a section capture instead of full-page (--selector)
outcome: exemplar screenshots land in <refs>/exemplars/, each recorded by one most-recent-first manifest row, ready for owner taste-file annotation
outputs: PNG file(s) in <refs>/exemplars/; a row appended to <refs>/exemplars/manifest.md per successful capture (filename, source_url, capture_date, viewport, scope); non-zero exit and no file/row on a failed capture
tags: [design, capability]
---

# screenshot-capture

Captures full-page or section screenshots of real, live URLs and lands them in a project's reference
set as CURATED EXEMPLARS — images the owner will annotate for taste, tone, and craft — never QA
throwaway screenshots, which belong to the browser-automation skill's own screenshots folder and are
deleted after use. Do not write exemplar output anywhere else, and do not treat this manifest as a
place for anything but curated captures.

This capability is design's own; it consumes the browse module's Chromium automation as
infrastructure, not as its home — driving a browser is the means, building the exemplar set is the
job.

## Entry point

```bash
python3 tool/capture.py --url <URL> [--url <URL> ...] --refs <reference-set-path> \
  [--viewport <WxH>] [--selector <css-selector>]
```

Full flag reference is self-documented: `python3 tool/capture.py -h`.

## Procedure

1. Confirm the target reference-set path exists (or let the tool create `<refs>/exemplars/` on first
   run) and that it is a real, persistent reference set for the current project — never a scratch or
   temp directory.
2. Run the tool with one `--url` per site to capture. Omit `--selector` for a full-page capture;
   supply a CSS selector to capture one section instead.
3. Read the tool's own stdout line per capture (`OK: <filename> (<w>x<h>) from <url>`) to confirm the
   measured dimensions match the requested viewport.
4. Open `<refs>/exemplars/manifest.md` to confirm one row landed per successful capture, most-recent
   row first, with columns `filename | source_url | capture_date | viewport | scope`.
5. Hand the reference set to the owner (or a downstream design step) for taste-file annotation —
   annotation and curation happen outside this capability.

## Behavior contract

| Situation | Result |
|---|---|
| No `--selector` | Full-page capture at the requested viewport; height capped at 16000px if the page exceeds it, noted in the manifest scope |
| `--selector <css>` | Only the matched element is captured; manifest scope records `section (<selector>)` |
| Same-day filename collision | The new file gets a versioned name (`-v2`, `-v3`, …) — an existing curated exemplar is NEVER overwritten |
| Byte-identical duplicate capture | Warning to stderr naming both files; the capture still lands |
| Dead URL / navigation timeout | Non-zero exit for that URL; no file written; no manifest row inserted |
| Consent/cookie overlay survives best-effort dismissal | Capture proceeds; manifest scope is flagged `overlay-present` so the owner knows to re-curate manually |

## Dependencies

`playwright` (Chromium headless) and `Pillow`, both already provided by this component's dependency
manifest. No other package is required — the tool does not import `requests`.

## Out of scope

Curation and taste judgment (owner annotates the taste file) · token extraction (`design-tokens`) ·
motion extraction (`subtle-refs`) · editing or retouching captures.
