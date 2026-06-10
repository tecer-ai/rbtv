# Studio

## Purpose

The studio module — everything that turns narrative and strategy into polished HTML artifacts: visual deck design, AI image prompts, brand visual identity, design-token extraction from live sites, and the browser automation layer that captures and validates rendered output. The office-module pitchers delegate all HTML building here; the module also works standalone for any design or browser-automation task.

The module also owns **hypresent** — the HTML presentation engine (not installable: not a command/skill/rule, but part of the module). It lives at `studio/hypresent/`.

---

## Components

### Studio Loop — the phase spine (`studio/workflows/studio-loop/`)

- **What**: The artifact-general four-beat HTML pipeline that turns an owner's brief + this project's reference set into an owner-accepted artifact: **message-lock (Strategist) → art-direction → generate (trio → slices → fresh-eyes) → human gate.** Artifact (deck/site/app) and mode (blank-slate) are PARAMETERS each beat adapts to, never top-level branches. It replaces the old `deck-design` workflow. Behavior is governed by the deck-loop-spec in the design-module plan folder.
- **Files**: `workflow.md` (spine entry + artifact/mode fork rules) and four beats under `beats/` — `beat-01-message-lock.md`, `beat-02-art-direction.md`, `beat-03-generate.md` (folds trio + slices + fresh-eyes), `beat-04-human-gate.md`.
- **How it runs**: The Strategist runs beat 1 and hands a content spec to the Designer (Vivian), who runs beats 2–4. Every worker resumes from **design-state + the reference set ALONE** — zero conversation context. Output is HTML-native (full-screen browser + print-to-PDF CSS); no PPTX.
- **Entry (v1)**: module-internal — reached via the already-installed `/rbtv-pitcher` (office), retargeted to the loop at P4.

---

### The Strategist (`studio/personas/strategist.md`)

- **What**: One message-lock persona with audience MODES (investor ← Roelof-mined, client ← Leo-mined; site-marketing + app-product are P5 stubs). Sits on the audience's side of the table, locks the deck's message, and authors the content spec — what to say and what each datum must communicate. NEVER makes a visual-design decision. Every external-facing number is owner-supplied and owner-sourced; an unsourced claim BLOCKS its slide, never fabricated.
- **When to use**: Beat 1 of the studio loop — before any design exists. Reached via `/rbtv-pitcher`'s Lock-the-Message entry.
- **What it produces**: The content spec (thesis · one point per slide · narrative arc · per-datum communication intent · owner-sourced numbers) + initialized design-state. Hands off to Vivian.

---

### `rbtv-designing` (Vivian — the Studio Designer)

- **What**: Vivian is the studio loop's visual worker — **art-direction → layout → visual**, downstream of the message. She consumes the Strategist's locked content spec + design-state and makes it awesome and distinct; she NEVER authors or alters the message. She offers ≥2–3 genuinely distinct directions and names which one she believes in, pushes past the safe choice, and obeys the ban-list. She resumes any run from design-state alone — the loop's visual memory lives on disk.
- **When to use**: After the message is locked (Strategist beat 1). Run the art-direction beat (mini-briefs → owner pick), generate the deck (trio → slices → fresh-eyes), and the human gate (accept/bounce → print-to-PDF). The Strategist hands off here automatically; you can also resume her standalone from a design-state path.
- **How to invoke**: `rbtv-designing` (skill, not a slash command). Menu options: `PD` (enter the loop at art-direction), `GEN` (generate HTML — trio/slices/fresh-eyes, beat 3), `GATE` (human gate — review/accept/bounce/print, beat 4), `BV` (brand visual identity — routes to the innovation module).
- **What it produces**: Owner-picked art direction; a pairwise-picked template trio (the visual contract); a full HTML deck generated slice-by-slice; a fresh-eyes punch-list; an owner-accepted deck printed to PDF — all recorded in design-state.
- **Example**: The Strategist hands off: "Calling Vivian." Vivian opens: "I'm seeing a steel-and-gold palette — quiet authority. Here are three directions."

---

### Standards bundle (`studio/standards/`)

- **What**: The module-internal standards that make "world-class AND distinct" a testable gate — `ban-list.md` (the default-attractor + mined-correction catalogue every art-direction brief and every slide must obey) and `flaw-checklist.md` (the ~10-item structural checklist the fresh-eyes pass runs against the rendered deck). Module-enforced; the reference set + taste file are workspace-owned.
- **When to use**: The art-direction beat checks every mini-brief against the ban-list; the fresh-eyes pass (beat 3) reviews against the flaw checklist + the chosen mini-brief.

---

### Design-state schema (`studio/state/design-state-schema.md`)

- **What**: The schema for `design-state.md` — the loop's mutable working memory (one file per run). It carries everything a fresh agent or an incoming worker (after a Strategist↔Designer switch) needs to resume mid-flight from design-state + the reference set alone. It RIDES the orchestration three-file state spine; it is a fourth artifact, never a fourth spine file.

---

### Reference-set scaffold (workspace-owned, at `5-workbench/tecer-biz/brand/studio-references/`)

- **What**: The four-layer reference set the loop LOADS and ENFORCES (never authors): tokens file (color/type/spacing/motion) + `exemplars/` screenshots + taste file (3–5 admirable-principle bullets per exemplar) + a chart exemplar. The contract is documented in `studio/standards/reference-set-contract.md`; the module HALTS on any missing layer.

---

### `/rbtv-design-extractor`

- **What**: Navigates a live website, captures multiple pages via screenshot + DOM/CSS extraction, and produces structured design token documentation — colors, typography, spacing, layout, CSS variables. Outputs a design brief and/or `design-tokens.json`.
- **When to use**: You want to clone, adapt, or analyze a competitor's or reference site's visual system before starting a design project. Feeds directly into Vivian's brand work.
- **How to invoke**: `/rbtv-design-extractor` (command). Provide a URL. The workflow maps the site, confirms the capture list with you, then extracts.
- **What it produces**: Design brief (markdown) and/or `design-tokens.json` with every token sourced to `"dom"` or `"screenshot-sampled"`.
- **Example**: `/rbtv-design-extractor` → `https://competitor.com` → workflow captures 6 pages, extracts 47 tokens, outputs `design-brief.md` and `design-tokens.json`.

---

### `/rbtv-vision-to-json`

- **What**: Forensically analyzes ONE static reference image into a strict JSON spec of every visual property, plus three generator-ready regeneration prompts (Nano-Pro, Flux, Midjourney) that recreate the image faithfully. This is photo forensics → regeneration prompt — distinct from `/rbtv-design-extractor`, which extracts UI design tokens from a live DOM.
- **When to use**: You have a reference photo or rendered image you want to reproduce or adapt. The legacy `deck-design` workflow's image step (`studio/workflows/deck-design/steps-c/step-02-images.md`) routes any slot for which the user supplies a reference image through this workflow to produce that slot's regeneration prompt (callable until `deck-design` is retired at P4).
- **How to invoke**: `/rbtv-vision-to-json` (command). Provide an image path or attachment.
- **What it produces**: `vision-to-json-{image-name}.json` plus three ready-to-paste regeneration prompts.
- **Example**: `/rbtv-vision-to-json` → reference hero shot → JSON spec + a Flux/Midjourney/Nano-Pro prompt that reproduces it.

---

### `rbtv-playwright-cli`

- **What**: Browser automation via Playwright CLI — takes screenshots, runs interactions, and tests web pages. Restricts Bash permissions to `playwright-cli:*` commands only.
- **When to use**: Automating browser tasks, capturing page screenshots, or testing web UI — including validating rendered HTML decks and extracted designs.
- **How to invoke**: "Take a screenshot of X" or "test this page interaction" — or `rbtv-playwright-cli` directly.
- **Inputs / outputs**: URL or interaction description → screenshots, test results, or extracted page state
- **Example**: "Screenshot the current state of our staging dashboard" → Claude runs Playwright CLI and returns the image.

---

## How They Fit Together

The **studio loop** is the spine: the **Strategist** locks the message (beat 1) and hands a content spec + initialized design-state to **Vivian** (`rbtv-designing`), who runs art-direction (beat 2 — mini-briefs picked against the reference set + ban-list), generation (beat 3 — pairwise trio → slice-by-slice deck → fresh-eyes pass against the flaw checklist), and the human gate (beat 4 — headed accept/bounce, surgical patch, bounce-cap escalation, print-to-PDF). Every worker resumes from **design-state** (`studio/state/`) + the workspace **reference set** alone — zero conversation context. The **standards bundle** (`studio/standards/`) makes "world-class AND distinct" testable: the ban-list gates every direction and slide; the flaw checklist drives the fresh-eyes pass.

Supporting capabilities feed the loop on demand: `/rbtv-design-extractor` captures a reference visual system into design tokens; `/rbtv-vision-to-json` turns a reference image into a regeneration prompt; `rbtv-playwright-cli` renders, screenshots, and QAs the result (it powers the headed renders the loop and the done-gate evidence depend on — `file://` is blocked, the loop uses a local HTTP server). The office-module pitchers enter the loop via the `/rbtv-pitcher` handoff (retargeted to the studio loop at P4). The legacy `deck-design` workflow is replaced by the studio loop and retired after the GSMM proof passes (`PI`/`PDF`/`DE` deck-design steps folded into the loop beats).
