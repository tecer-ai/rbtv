---
inputs: "--url (repeatable, required) — target URL; live or local-server only, file:// refused. --out (required) — markdown report path. --json-out (optional) — raw observation array per URL. --headed (optional) — run the browser visibly, for debugging."
outcome: "The motion and interaction character of one or more live pages — animation timings, easings, scroll behaviours, hover states, transitions, micro-interactions — captured as a grounded, anchored report an art-direction brief can cite."
outputs: "A markdown report at --out: one section per URL, one row per observation (pattern, element anchor, observed values, where seen). A page with no detected motion still produces a valid report carrying a settle-uncertain observation. Optional JSON at --json-out mirrors the same observations."
exposes-cli:
  - subtle-refs-cli
---

# subtle-refs

Extracts the MOTION and INTERACTION character of a live URL — how things move and respond, not
what they look like. Use this capability, and not one of its siblings, by what the consumer needs:

- **subtle-refs** (this capability) — animation timings, easings, transitions, scroll behaviour,
  hover states, micro-interactions.
- **`design-tokens`** — colour, type, and spacing tokens. Run that instead when the brief needs a
  palette or a type scale, not how the page moves.
- **`screenshot-capture`** — curated exemplar images of a reference site. Run that instead when the
  brief needs a picture to look at, not a description of behaviour.

A single reference site is commonly run through more than one of these; each capability owns its
own slice and none restates another's output.

## Entry point

```bash
python tool/extract.py --url <URL> [--url <URL2> ...] --out <report.md> [--json-out <report.json>] [--headed]
```

Full flag reference is the tool's own `--help` (`python tool/extract.py -h`) — this file does not
restate it.

## Dependencies

Python 3.12+, `playwright` (`python -m pip install playwright`) with the Chromium browser installed
(`python -m playwright install chromium`).

## Procedure

1. Confirm the target is a live URL or a local-server address — `file://` is refused by the tool
   itself; do not attempt to route around that with a local path.
2. Invoke the entry point with one `--url` per reference site and an `--out` report path.
3. The tool loads each real page in Chromium, waits for network idle plus a settle period, then
   reads computed CSS transitions and animations, `@keyframes` rules, `:hover` rules that touch
   motion properties, scroll-behaviour, known JS animation libraries, and scroll-trigger attribute
   hints.
4. Read the report. Every row must carry a concrete element anchor (a selector or DOM description)
   and concrete observed values (duration, easing, transform, or trigger) — a row with neither is a
   defect in the tool, not something to paper over by hand.
5. For a page that shows no motion, the report carries a `settle-uncertain` observation instead of
   an empty section — this is itself the valid result, not a failure to fix.
6. For an unreachable URL, the tool exits non-zero and writes no report claiming success. Do not
   retry into a synthetic report — report the failure upward as-is.

## `settle-uncertain` — what it means, and what it never means

A `settle-uncertain` result means exactly one of two things: the page is genuinely static, or motion
exists but had not attached by the settle window (network-idle plus a fixed wait). It is a valid,
honest outcome — exit 0, a real report on disk.

It NEVER licenses inventing an observation to fill the report. If the page cannot be settled, or is
blocked from loading properly (a bot wall, a consent gate that never clears, a heavy single-page app
that never reaches network-idle), the report states that limitation in plain terms. A fabricated
timing or easing value — one not read from the live page's computed style — is a failure of this
capability, not a workaround for a hard page.

## Report row contract

One row per observation, and one report section per URL:

- **Pattern** — what kind of thing was observed (css-transition, css-animation, keyframes-catalog,
  hover-rules, js-animation-library, scroll-trigger-hints, scroll-behavior, or settle-uncertain).
- **Element anchor** — a CSS selector or plain description of what was observed.
- **Observed values** — the concrete duration, easing, transform, or trigger read from the page.
- **Where seen** — the URL the observation came from.

## Out of scope

Colour, type, and spacing tokens (`design-tokens`); screenshot capture (`screenshot-capture`);
copying content or code from a reference site; judging whether the observed motion is good design —
that judgment belongs to the art-direction brief and the owner, not this capability.
