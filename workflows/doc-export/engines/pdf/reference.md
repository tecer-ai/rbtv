# md-to-pdf Reference

Markdown -> HTML (via Marked) -> PDF (via Puppeteer/headless Chromium). All modern CSS works. GFM tables, code highlighting (highlight.js), and images are supported.

## CLI Options

| Flag | Purpose |
|------|---------|
| `--stylesheet path.css` | Custom CSS file (repeatable). **Replaces** built-in styles |
| `--css "body { color: red; }"` | Inline CSS string |
| `--config-file config.js` | JS or JSON config file (full control -- needed for logos) |
| `--pdf-options '{...}'` | Puppeteer PDF options as JSON |
| `--highlight-style monokai` | Code block theme (any highlight.js theme) |
| `--document-title "Title"` | Sets document title (used in header `<span class="title">`) |
| `--as-html` | Output HTML instead of PDF (for debugging) |
| `--watch` | Re-generate on file change |
| `--basedir path` | Base directory for resolving relative paths |

**Priority order** (low -> high): defaults -> config file -> frontmatter -> CLI arguments.

## PDF Options (Puppeteer passthrough)

Set via `--pdf-options` CLI flag, `pdf_options` in config/frontmatter.

| Option | Type | Default | Notes |
|--------|------|---------|-------|
| `format` | string | `A4` | `A4`, `A5`, `Letter`, `Legal`, `Tabloid` |
| `landscape` | boolean | `false` | Landscape orientation |
| `margin` | object/string | `30mm 40mm 30mm 20mm` | CSS shorthand or `{top, right, bottom, left}` |
| `printBackground` | boolean | `true` | Print CSS backgrounds |
| `headerTemplate` | string | -- | HTML for page header (read `branding.md`) |
| `footerTemplate` | string | -- | HTML for page footer (read `branding.md`) |

## Frontmatter Configuration

YAML frontmatter in the markdown file. All config keys use underscores.

```yaml
---
dest: ./output.pdf
stylesheet:
  - path/to/style.css
css: |-
  body { color: #333; }
pdf_options:
  format: A4
  margin: 30mm 20mm
  printBackground: true
---
```

**Note:** `dest` controls output path. Stylesheet paths resolve relative to the markdown file.

## Page Breaks

```html
<div class="page-break"></div>
```

## Gotchas

| Issue | Solution |
|-------|----------|
| Windows EPERM spawn error | Antivirus blocks Chromium -- whitelist Puppeteer's cache dir |
| Windows EBUSY on regenerate | PDF is open in a viewer or indexed by Obsidian. md-to-pdf cannot write to the file -- even `--pdf-options path` to an alternate name fails (it still tries to open the original). Fix: close the viewer, then `rm` the old PDF before regenerating |
| Images not loading in header/footer | Use base64 data URLs via config.js -- read `branding.md` |
| Header/footer text invisible | Set font-size explicitly (defaults to 1pt) |
| Content overlaps header | Increase top margin to clear header height |
| `--stylesheet` replaces built-in CSS | Include base styles or use `--css` for additions |
