# Exemplar-Screenshot Capture Capability

> Self-contained CLI for capturing curated exemplar screenshots into a project's reference set.

## Entry Point

```bash
python studio/capabilities/screenshot-capture/capture.py \
  --url <URL> [--url <URL> ...] \
  --refs <reference-set-path> \
  [--viewport <WxH>] \
  [--selector <css-selector>]
```

## Inputs

| Flag | Required | Default | Description |
|------|----------|---------|-------------|
| `--url` | Yes (repeatable) | — | Target page(s) to capture |
| `--refs` | Yes | — | Path to the reference set (must contain `exemplars/`; manifest is `exemplars/manifest.md`) |
| `--viewport` | No | `1440x900` | Browser viewport dimensions, e.g. `1920x1080` |
| `--selector` | No | — | CSS selector for a section capture instead of full-page |

## Outputs

- PNG file(s) in `<refs>/exemplars/`
- One manifest row appended per capture to `<refs>/exemplars/manifest.md`

## Dependencies

Pre-installed in this environment:

- `playwright` (Chromium headless)
- `Pillow`
- `requests`

No additional packages required.

## Behavior

| Mode | Trigger | Result |
|------|---------|--------|
| Full-page | No `--selector` | Entire page rendered at `--viewport`; file capped at 16000 px height if necessary |
| Section | `--selector <css>` | Only the matched element is captured |
| Versioning | Filename collision on same day | Automatic `v{N}` suffix; existing files are never overwritten |
| Dead URL | Navigation failure / timeout | Non-zero exit; no file written; no manifest row appended |
| Overlays | Cookie / consent banners survive dismissal | Capture proceeds; manifest scope flags `overlay-present` |

## Manifest Row Contract

Each successful capture appends one row with the fields required by the reference-set manifest:

```
| filename | source_url | capture_date | viewport | scope |
```

Read `studio-references/exemplars/manifest.md` for the canonical row format.

## Examples

```bash
# Two full-page captures at default viewport
python studio/capabilities/screenshot-capture/capture.py \
  --url https://stripe.com \
  --url https://www.apple.com \
  --refs C:/Users/henri/.../studio-references

# Section capture at custom viewport
python studio/capabilities/screenshot-capture/capture.py \
  --url https://stripe.com/pricing \
  --refs C:/Users/henri/.../studio-references \
  --viewport 1920x1080 \
  --selector "[data-testid='pricing-table']"
```
