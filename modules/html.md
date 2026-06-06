# HTML

## Purpose

The HTML power-up module — everything that turns narrative and strategy into polished HTML artifacts: visual deck design, AI image prompts, brand visual identity, design-token extraction from live sites, and the browser automation layer that captures and validates rendered output. The office-module pitchers delegate all HTML building here; the module also works standalone for any design or browser-automation task.

The module also owns **hypresent** — the HTML presentation engine (not installable: not a command/skill/rule, but part of the module). It lives at `html/hypresent/`.

---

## Components

### `rbtv-designing` (Vivian)

- **What**: Vivian is the visual layer for both pitch flows — a Creative Director who translates strategy into HTML deck design, AI image prompts, and brand visual identity. She always offers three visual directions and names which one she believes in. Design is explicitly downstream of narrative: she never redoes strategic work. Her pitch work runs the module's `deck-design` workflow (`html/workflows/deck-design/`), which consumes the pitch artifacts (`pitch-narrative.md` + `pitch-structure.md`) from disk — a fresh session needs zero conversation context.
- **When to use**: After narrative is locked (office pitcher step 6) and you're ready to generate the HTML deck, produce AI image prompts, export to PDF, edit an existing deck, or design brand visual guidelines. The pitchers hand off here automatically — you can also invoke her standalone for any of those tasks.
- **How to invoke**: `rbtv-designing` (skill, not a slash command). Menu options: `PD` (full deck design + export), `PI` (image prompts only), `PDF` (PDF export + QA), `DE` (deck edit — content + visual, with narrative/structure back-sync), `BV` (brand visual identity).
- **What it produces**: Branded HTML deck, a set of AI image prompts ready to paste into Midjourney/DALL-E, PDF via Decktape, edited decks kept in sync with their narrative artifacts, visual brand guidelines.
- **Example**: After Leo finishes the narrative, she hands off: "Calling Vivian." Vivian opens: "I'm seeing a steel-and-gold palette — quiet authority. Here are three directions."

---

### `/rbtv-design-extractor`

- **What**: Navigates a live website, captures multiple pages via screenshot + DOM/CSS extraction, and produces structured design token documentation — colors, typography, spacing, layout, CSS variables. Outputs a design brief and/or `design-tokens.json`.
- **When to use**: You want to clone, adapt, or analyze a competitor's or reference site's visual system before starting a design project. Feeds directly into Vivian's brand work.
- **How to invoke**: `/rbtv-design-extractor` (command). Provide a URL. The workflow maps the site, confirms the capture list with you, then extracts.
- **What it produces**: Design brief (markdown) and/or `design-tokens.json` with every token sourced to `"dom"` or `"screenshot-sampled"`.
- **Example**: `/rbtv-design-extractor` → `https://competitor.com` → workflow captures 6 pages, extracts 47 tokens, outputs `design-brief.md` and `design-tokens.json`.

---

### `rbtv-playwright-cli`

- **What**: Browser automation via Playwright CLI — takes screenshots, runs interactions, and tests web pages. Restricts Bash permissions to `playwright-cli:*` commands only.
- **When to use**: Automating browser tasks, capturing page screenshots, or testing web UI — including validating rendered HTML decks and extracted designs.
- **How to invoke**: "Take a screenshot of X" or "test this page interaction" — or `rbtv-playwright-cli` directly.
- **Inputs / outputs**: URL or interaction description → screenshots, test results, or extracted page state
- **Example**: "Screenshot the current state of our staging dashboard" → Claude runs Playwright CLI and returns the image.

---

## How They Fit Together

`/rbtv-design-extractor` captures a reference visual system → Vivian (`rbtv-designing`) turns narrative + design tokens into a branded HTML deck, image prompts, and PDF → `rbtv-playwright-cli` renders, screenshots, and QAs the result. The office-module pitchers enter this flow at their step-6 handoff, through the `pitch-narrative.md` + `pitch-structure.md` artifacts (deck-design's v0 input contract). Deck editing also lives here — Vivian's `DE` keeps HTML, narrative, and structure in sync; story-level rework routes back to the pitchers.
