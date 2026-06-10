# extract-subtle-refs

Extract motion and interaction character from a live reference URL.

## Entry point

```bash
python studio/capabilities/extract-subtle-refs/extract.py --url <URL> --out <report.md>
```

## Dependencies

- Python 3.12+
- `playwright` (`python -m pip install playwright`)
- Playwright Chromium (install via `python -m playwright install chromium`)

## Inputs

| Flag | Required | Description |
|------|----------|-------------|
| `--url` | Yes | Target URL. Repeatable for multiple URLs. |
| `--out` | Yes | Output markdown report path. |
| `--json-out` | No | Optional JSON output path. |
| `--headed` | No | Run browser in headed mode (for debugging). |

## Outputs

- **Markdown report** (`--out`): One section per URL. Each observation carries a pattern name, element anchor, observed values (duration/easing/transform/trigger), and a note.
- **Optional JSON** (`--json-out`): Raw observation array per URL.

## Behavior

1. Loads the real page in Chromium (headless by default).
2. Waits for network idle + 2-second settle period.
3. Extracts:
   - CSS transitions with non-zero duration.
   - CSS animations with non-zero duration.
   - `@keyframes` rules from stylesheets.
   - `:hover` selectors that reference motion properties.
   - Scroll-behavior setting.
   - Detected JS animation libraries (GSAP, anime.js, AOS, etc.).
   - Scroll-trigger attribute hints (`data-aos`, `data-sr`, `data-scroll`).
4. If no motion patterns are found, the report emits a `no-detectable-motion` observation whose note states that no CSS transitions, animations, hover motion rules, keyframes, JS animation libraries, or scroll-trigger attributes were detected. A static page therefore always yields a report (never an empty file): the `scroll-behavior` structural row plus the `no-detectable-motion` row. NOTE: a heavy or slow page whose motion has not yet attached when the settle window closes produces this SAME no-motion result with exit 0 — an empty-findings report is not proof the page is static.
5. If the page is unreachable, exits non-zero with a reason written to stderr; no success report is produced.
6. For heavy SPAs that cannot settle, the report names the limitation.

## Exit codes

| Code | Meaning |
|------|---------|
| 0 | Success — report written. |
| 1 | One or more URLs failed to load or produced an error. |
