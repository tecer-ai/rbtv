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

- **Markdown report** (`--out`): One section per URL. Each observation carries a pattern name, element anchor, observed values (duration/easing/transform/trigger), and a note. A zero-motion result is reported as `settle-uncertain`, because the page may be static OR the settle window may have missed late-attaching motion.
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
4. If no motion patterns are found, the report emits a `settle-uncertain` observation whose note states that zero motion was detected, and that the page may be genuinely static OR motion may not have attached by the settle window (`networkidle` + 2s). The CLI also writes `WARN: settle-uncertain: <url> — zero motion; static OR settle missed it` to stderr. This warning does not change exit-code behavior: a reachable static or uncertain page still exits 0.
5. If the page is unreachable, exits non-zero with a reason written to stderr; no success report is produced.
6. For heavy SPAs that cannot settle, the report names the limitation.

## Exit codes

| Code | Meaning |
|------|---------|
| 0 | Success — report written. |
| 1 | One or more URLs failed to load or produced an error. |
