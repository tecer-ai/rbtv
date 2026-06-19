# Studio

## Purpose

The studio module — everything that turns narrative and strategy into polished HTML artifacts: the studio loop entry (`/rbtv-strategist` — opens the Strategist for message-lock), visual deck design, AI image prompts, brand visual identity, design-token extraction from live sites, and the browser automation layer that captures and validates rendered output. The loop is entered through this module's own `/rbtv-strategist` command; the module also works standalone for any design or browser-automation task.

**Install status: INSTALLED (as of 2026-06-10 — owner-approved at p6-checkpoint).** The studio module is in the install set. Five surfaces are live in `.claude/`: the `rbtv-designing` skill (Vivian, the Designer) and `rbtv-playwright-cli` skill (browser automation), and the `/rbtv-strategist`, `/rbtv-design-extractor`, and `/rbtv-vision-to-json` commands. `/rbtv-strategist` (moved from office and renamed from `/rbtv-pitcher`, 2026-06-10) opens the Strategist for message-lock. The studio loop beats, the artifact forks (`forks/site.md`, `forks/app.md`), and the critic remain loop-internal BY DESIGN — they are reached via `/rbtv-strategist` → the studio loop, not as standalone commands.

The module also owns **hypresent** — the HTML presentation engine (not installable: not a command/skill/rule, but part of the module), backed by the **slide-library** convention + engine (`studio/slide-library/`) that organizes slides for it. The slide-library manifest carries an optional 11th `status` column (`to-review` | `ready`, additive, missing → `ready`); existing 10-column libraries assemble unchanged. The slide-library also ships an **archive tool** (`engine/archive.py`) that retires a superseded fragment into an `archive/` folder the engine never reads, and restores it losslessly — keeping `slides/` to the live set (spec § 1.3). Both are resident subtrees the studio loop never *requires* and never modifies in `studio/`; they live at `studio/hypresent/` and `studio/slide-library/`. Beat 3 MAY *optionally* reuse a spec-compliant slide library found in the working repo (e.g. a client's `slide-library/` at its repo root) when one fits the deck — owner-gated, never required (beat-03 § 3·0).

The module also owns **deck→library export** — an in-app capability in hypresent that lets an owner, with a deck open, visually select slides and export them into the slide-library as `<section>`-only fragments with manifest rows tagged `status: to-review`. This is the reverse path of the library→deck assembly the engine already supports. It is in-app only (decompose engine + `/api/deck-export` endpoint + the `/api/library-validate-target` endpoint that the "Choose…" target-library picker validates against — path-only, matching what export actually requires, NOT the full catalog-load engine — + builder UI controls); no new command, skill, or rule was added. The export is gated on the deck carrying per-slide `data-hyp-*` export-metadata attributes, 1280×720 slide sizing, and a `@media print` block — the authoring standard defined in `studio/slide-library/docs/convention-spec.md` § 10. Dashboard/app output is exempt from this standard.

---

## Dependencies

The studio (design) module depends on the **writing** module for one shared standard:

- **`writing/workflows/writing/data/ai-anti-patterns.md`** (AI writing anti-patterns). The canonical catalogue of AI-tell writing patterns: generic phrasing, edge erosion, list-ification, the em-dash crutch, and the rest. **Wired in 2026-06-17:** the Strategist's message-lock (`studio/workflows/studio-loop/beats/beat-01-message-lock.md`) authors content-spec copy clean of these tells, and the Designer's fresh-eyes pass (`beat-03-generate.md` §3C) audits the rendered deck copy against it alongside the flaw-checklist. Deck copy is prose-light, so the surface categories apply most; the narrative-essay categories (premature resolution, emotional flattening) are advisory there.

This is a **source-file dependency** within the rbtv repo: the studio beats reference the writing doc by `{rbtv_path}/writing/...` path (live on `git pull`). It is present whenever rbtv is present, independent of whether the writing module's commands are installed in `.claude/`.

---

## Components

### Studio Loop — the phase spine (`studio/workflows/studio-loop/`)

- **What**: The artifact-general four-beat HTML pipeline that turns an owner's brief + this project's reference set into an owner-accepted artifact: **message-lock (Strategist) → art-direction → generate (trio → slices → fresh-eyes) → human gate.** Artifact (deck/site/app) and mode (blank-slate) are PARAMETERS each beat adapts to, never top-level branches. Behavior is governed by the deck-loop-spec (`studio/deck-loop-spec.md`).
- **Files**: `workflow.md` (spine entry + artifact/mode fork rules) and four beats under `beats/` — `beat-01-message-lock.md`, `beat-02-art-direction.md`, `beat-03-generate.md` (folds trio + slices + fresh-eyes), `beat-04-human-gate.md`.
- **How it runs**: The Strategist runs beat 1 and hands a content spec to the Designer (Vivian), who runs beats 2–4. Every worker resumes from **design-state + the reference set ALONE** — zero conversation context. Output is HTML-native (full-screen browser + print-to-PDF CSS for decks; responsive multi-page HTML for sites; plain-HTML designed screens for apps); no PPTX.
- **Entry**: `/rbtv-strategist` (studio) — opens the Strategist for beat 1; the Designer (`rbtv-designing`) runs beats 2–4.

#### Artifact forks (`studio/workflows/studio-loop/forks/`)

Two artifact branches extend the loop for sites and apps. Each is a single file under `forks/`; both ride beats 2–4 of the deck loop unchanged, with only the discovery/structure beat and output contract replaced.

- **`forks/site.md`** — `artifact: site` branch. Adds the **site structure beat** (§A) where the Strategist produces a sitemap + per-page narrative (one communication goal per page, never per-slide), then hands off to the deck loop's art-direction / template / slice / fresh-eyes / human-gate beats parameterized for PAGES. The **site output contract** (§B) replaces the deck's print-to-PDF contract with responsive multi-page HTML (cross-linked pages, desktop + mobile viewports, real-provenance imagery via image-gen, motion within the chosen direction's character). Deck beats 2–4 are reused unchanged via §C downstream wiring — the site fork adds ONE new beat and ONE replaced contract. Runs in the `site-marketing` Strategist mode.
- **`forks/app.md`** — `artifact: app` branch. Forks EARLIER than sites (at discovery): the Strategist runs THREE discovery beats (§A goals → §B user-flow → §C UX) instead of the deck slide-narrative, producing testable user goals, a reachable flow map, and per-screen UX companion docs. The **app output contract** (§D) replaces the deck contract with plain-HTML screens with designed states (every state named in the UX doc visibly designed — never happy-path-only), responsive at both viewports, ZERO application code. The package — HTML screens + UX companion docs + flow map — is the coding-agent handoff; a fresh coding agent wires the real app from it alone. Deck beats 2–4 reused via §E. Runs in the `app-product` Strategist mode.

---

### The Strategist (`studio/personas/strategist.md`)

- **What**: One message-lock persona with four audience MODES. Sits on the audience's side of the table, locks the artifact's message (or discovery, for apps), and authors the content spec — what to say and what each datum must communicate. NEVER makes a visual-design decision. Every external-facing number is owner-supplied and owner-sourced; an unsourced claim BLOCKS its slide/page/screen, never fabricated.
- **Audience modes** (resolved at activation from design-state `audience_mode` or by asking):
  - `investor` — mined from the retired Roelof persona; VC partner's seat; standard 13-slide investor arc.
  - `client` — mined from the retired Leo persona; VP-of-Procurement's seat; standard 11-slide client arc.
  - `site-marketing` — target-visitor's seat; pain→desire arc, one communication goal per page; feeds `forks/site.md` §A (site structure beat).
  - `app-product` — app-user + product-owner's dual seat; goal-led discovery (testable user goals → flow → UX companion docs); feeds `forks/app.md` §A–§C.
- **When to use**: Beat 1 of the studio loop — before any design exists.
- **How to invoke**: `/rbtv-strategist` (command) — the Strategist opens and resolves the audience mode (or is reached automatically when the loop runs).
- **What it produces**: Content spec (thesis · one point per slide/page/screen · narrative arc · per-datum communication intent · owner-sourced numbers) + initialized design-state. For apps: also per-screen UX companion docs (§C / `ux-companion-docs-contract.md`). Hands off to Vivian.

---

### `rbtv-designing` (Vivian — the Studio Designer)

- **What**: Vivian is the studio loop's visual worker — **art-direction → layout → visual**, downstream of the message. She consumes the Strategist's locked content spec + design-state and makes it awesome and distinct; she NEVER authors or alters the message. She offers ≥2–3 genuinely distinct directions and names which one she believes in, pushes past the safe choice, and obeys the ban-list. She resumes any run from design-state alone — the loop's visual memory lives on disk. She PROACTIVELY identifies where an image strengthens the artifact and proposes it to the owner (purpose + style); on owner-yes she generates it via the `image-gen` capability and positions it. Imagery is owner-gated and real-provenance only; she degrades gracefully — proposes but flags "needs the Gemini key" and offers the `fixture` placeholder — when `GEMINI_API_KEY` or the `gemini` adapter is absent. Prompt craft, style selection, when-to-propose heuristics, and placement rules are governed by the craft guide at `studio/capabilities/image-gen/image-craft.md`.
- **When to use**: After the message is locked (Strategist beat 1). Run the art-direction beat (mini-briefs → owner pick), generate the deck (trio → slices → fresh-eyes), and the human gate (accept/bounce → print-to-PDF). The Strategist hands off here automatically; you can also invoke `rbtv-designing` directly to resume from a design-state path.
- **How to invoke**: `rbtv-designing` (skill, not a slash command). Menu options: `PD` (enter the loop at art-direction), `GEN` (generate HTML — trio/slices/fresh-eyes, beat 3), `GATE` (human gate — review/accept/bounce/print, beat 4), `BV` (brand visual identity — routes to the innovation module), `IMG` (generate imagery — propose where an image strengthens the artifact, generate via `image-gen` on owner-yes, position it; degrades to `fixture` placeholder when Gemini is absent).
- **What it produces**: Owner-picked art direction; a pairwise-picked template trio (the visual contract); a full HTML deck generated slice-by-slice; a fresh-eyes punch-list; an owner-accepted deck printed to PDF — all recorded in design-state.
- **Example**: The Strategist hands off: "Calling Vivian." Vivian opens: "I'm seeing a steel-and-gold palette — quiet authority. Here are three directions."

---

### `rbtv-hypresent-comments` (Comment Resolution + Authoring Protocols)

- **What**: The MANDATORY protocol ANY agent follows when it acts on hypresent review comments on an HTML artifact. The skill is a thin router over two self-contained, mutually-exclusive procedures (an agent loads only the branch its task needs):
  - **Respond** (`comment-implementation.md`) — implement/answer/resolve EXISTING comments: reconcile the whole pass first (surface conflicting comments, order dependent ones), then for each — edit a NEW versioned copy (never overwrite), weigh the change's deck-wide ripple (propagate entailed consistency — repeated facts, dependent totals, numbering, TOC, cross-references — with disclosure; surface discretionary changes as new anchored comments for the owner), reply inline under the agent's own `{agent-name} ({role} agent)` identity stating what changed and everything else it touched, remove only the `data-hyp-agent` tag (never orphan the thread), re-anchor a kept comment on slide/element delete, and NEVER resolve or delete the human's thread (only the owner resolves).
  - **Author** (`comment-authoring.md`) — CREATE a new comment from scratch by invoking ONE tool, `studio/hypresent/tools/add_comment.py`: the agent passes a unique CSS selector + the comment text (+ its own author identity, optional `--agent`, optional `--out`), and the tool drives the real hypresent runtime headlessly to compute the anchor and save a valid file through the app's own save handler. The agent never reads runtime code, hand-writes the island, or computes an anchor — removing both the drift risk (a wrong anchor → invisible comment) and the parse risk (a hand-written island hiding all comments). Carries a confirm-intent gate (hypresent comment vs raw HTML comment) and a failure-mode guard: a review note left as a raw HTML `<!-- -->` comment is INVISIBLE in hypresent.
  - The thread is the human's audit record. Extracted from Vivian's studio loop (2026-06-15) so any agent — not just the Designer — follows it.
  - **Cheap reads** (`studio/hypresent/tools/dehydrate.py`) — either branch first generates a token-reduced read view (`<deck>.lean.html`): the visual layer (CSS, inline SVG, fonts, vendor JS) stripped, every `id`/`class`/section + both comment stores (digest + `#hyp-comments` island + agent block) kept, so an agent reads comments and crafts selectors off a much smaller file. A selector read off the lean view resolves in the real deck unchanged. DESIGN changes are the exception — read the full styling of the target, never the lean view.
- **When to use**: Any time an agent acts on comments in an HTML artifact — responding to a human gate / agent-tagged instruction block / direct owner request, OR leaving its own review note or instruction. The description fires on plain-language intent ("add comments to this HTML", "review the comments in this HTML", "annotate / resolve the comments") even when the user never says "hypresent" — so an agent never falls back to invisible raw HTML `<!-- -->` comments. It excludes literal code-explanation comments. Vivian (the Designer) is wired to it directly; any other agent auto-matches the skill by description.
- **How to invoke**: `rbtv-hypresent-comments` (skill, not a slash command). Backed by `studio/workflows/hypresent-comments/comment-implementation.md` (respond) and `studio/workflows/hypresent-comments/comment-authoring.md` (author).
- **What it produces**: Either a new versioned artifact with each requested change applied (plus any entailed deck-wide ripples and agent-surfaced comments for discretionary ones) and an inline agent reply on every implemented thread (respond), or the same artifact with a new agent-authored thread appended to the comment island (author) — in both cases threads are left unresolved for the owner.

---

### Standards bundle (`studio/standards/`)

- **What**: The module-internal standards that make "world-class AND distinct" a testable gate — `ban-list.md` (the default-attractor + mined-correction catalogue every art-direction brief and every slide must obey), `flaw-checklist.md` (the structural checklist the fresh-eyes pass runs against the rendered deck), `ux-companion-docs-contract.md` (the per-screen document format for the app fork's coding-agent handoff).
- **When to use**: The art-direction beat checks every mini-brief against the ban-list; the fresh-eyes pass (beat 3) reviews against the flaw checklist + the chosen mini-brief. The app fork's UX beat (forks/app.md §C) emits docs in the `ux-companion-docs-contract.md` format; the Designer keeps each screen's HTML in sync with its companion doc.
- **`ux-companion-docs-contract.md`** — the per-screen companion doc format that travels with each app-path HTML screen. Five required fields: screen goal (one job, traced to the goals beat) · flow position (from/to transitions) · states (empty/loading/error/success, each named) · interactions (every control accounted for) · acceptance notes (owner-observable wired-correctly criteria). Self-sufficiency bar: a fresh coding agent wires the real app from the package (HTML screens + companion docs + flow map) alone, without the designer.

---

### Design-state schema (`studio/state/design-state-schema.md`)

- **What**: The schema for `design-state.md` — the loop's mutable working memory (one file per run). It carries everything a fresh agent or an incoming worker (after a Strategist↔Designer switch) needs to resume mid-flight from design-state + the reference set alone. It RIDES the orchestration three-file state spine; it is a fourth artifact, never a fourth spine file.

---

### Reference-set scaffold (workspace-owned, at `{reference_set}/` — resolved at runtime per `rbtv-output-resolution`)

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
- **When to use**: You have a reference photo or rendered image you want to reproduce or adapt — use when building out a reference set or when a design slot calls for regenerating from a reference image.
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

### Capabilities (`studio/capabilities/`)

The module ships a registry (`studio/capabilities/registry.md`) that indexes every capability. Workers consult the registry for invocation details. Seven capabilities are registered:

| # | Name | Status | Entry point |
|---|------|--------|-------------|
| 1 | follow-tokens / brandbook | `convention` — woven into beats 2–4; no separate invocation | n/a |
| 2 | extract-tokens-from-site | `built` — live-site design-token extraction | `/rbtv-design-extractor` |
| 3 | image→JSON | `built` — reference image → strict JSON spec + regeneration prompts | `/rbtv-vision-to-json` |
| 4 | extract-subtle-refs | `built` — motion/interaction reference extraction from live URLs | `studio/capabilities/extract-subtle-refs/extract.py` |
| 5 | image-gen | `built` — source-pluggable AI image generation (Gemini provider first; live Gemini call requires a quota-carrying key — `free tier limit:0`; fixture provider available). Ships the Designer craft companion `studio/capabilities/image-gen/image-craft.md` — when-to-propose heuristics, style families, prompt anatomy, placement rules (Designer-facing; does not alter capability count or entry point) | `studio/capabilities/image-gen/generate.py` |
| 6 | exemplar-screenshot capture | `built` — headless Playwright screenshot capture into the reference-set `exemplars/` folder + manifest | `studio/capabilities/screenshot-capture/capture.py` |
| 7 | load-references | `built` — loads all four reference-set layers into working context; HALTS on any missing layer | `studio/capabilities/load-references.md` (procedural) |

Capabilities 4–6 are CLI Python scripts run from the repo root. Read each capability's usage doc before invoking.

---

### Critic (`studio/critic/`)

- **What**: The v1.1 comparative, taxonomy-driven critic — an **improver and stopping rule that NEVER gates**. Hand it two+ artifact variants (or one + the project reference set) and it returns: which variant is stronger per structural axis (pairwise, taxonomy-cited, element-anchored); a separate advisory-to-human aesthetic section (your call, never scored). No numeric scores, no pass/fail, no blocking the human gate (D1 — the human gate stays final and untouched).
- **Files**:
  - `critic.md` — the executable procedure (load taxonomy + reference set → render headed → structural pass → comparative verdict → advisory-to-human section → emit critique file). Four binding pins: comparative-never-absolute · taxonomy-driven · structural-auto/aesthetic-HUMAN split · per-project anchoring. Module-internal; not a `.claude/` install.
  - `taxonomy.md` — the structural flaw dataset: 10 axes (Hierarchy & Message · Contrast & Legibility · Alignment & Spacing · Overflow & Density · Type & Color System · Component Weight · Chart Communication · Cover/Closing & Parity · Data Integrity · Print/PDF Safety), each carrying item IDs (`T-H1` … `T-PR1`), flaw descriptions, how-to-spot notes, comparative cues, and borrowed-from IDs tracing to the ban-list/flaw-checklist. A genuinely structural flaw absent from the taxonomy is still reported as `T-UNCAT` + spotting cue for taxonomy growth.
- **Optional loop wiring (default OFF)**: the critic can be wired into the studio loop beats via the `critic: on` design-state frontmatter toggle (set in the design-state to opt in): beat-03 §3A (post-trio pairwise) and beat-04 step 2 (pre-gate attach). When off or absent, the loop runs exactly as shipped at P2. When on, the critic output is ATTACHED for the owner's review; the human gate proceeds regardless.
- **When to use**: On demand during any deck/site/app run to compare variants or get a structural flaw pass. Never as a gate; always as an improver.

---

## How They Fit Together

The **studio loop** is the spine: the **Strategist** locks the message (beat 1) and hands a content spec + initialized design-state to **Vivian** (`rbtv-designing`), who runs art-direction (beat 2 — mini-briefs picked against the reference set + ban-list), generation (beat 3 — pairwise trio → slice-by-slice deck → fresh-eyes pass against the flaw checklist), and the human gate (beat 4 — headed accept/bounce, surgical patch, bounce-cap escalation, print-to-PDF). Every worker resumes from **design-state** (`studio/state/`) + the workspace **reference set** alone — zero conversation context. The **standards bundle** (`studio/standards/`) makes "world-class AND distinct" testable: the ban-list gates every direction and slide; the flaw checklist drives the fresh-eyes pass; the `ux-companion-docs-contract.md` governs the app fork's coding-agent handoff.

The **artifact forks** extend the spine for sites and apps: `forks/site.md` routes `artifact: site` through a site-structure beat (sitemap + per-page narrative) before handing off to the deck's beats 2–4 with responsive multi-page HTML as the output; `forks/app.md` routes `artifact: app` through three discovery beats (goals → user-flow → UX companion docs) before the same shared beats produce plain-HTML designed screens. Both forks are activated by the `artifact` parameter in design-state; the deck path is unaffected. The **Strategist** resolves the matching audience mode at activation — `site-marketing` for sites, `app-product` for apps.

Supporting capabilities feed the loop on demand: `/rbtv-design-extractor` captures a reference visual system into design tokens; `/rbtv-vision-to-json` turns a reference image into a regeneration prompt; `rbtv-playwright-cli` renders, screenshots, and QAs the result (it powers the headed renders the loop and the done-gate evidence depend on — `file://` is blocked, the loop uses a local HTTP server). The `extract-subtle-refs`, `image-gen`, and `exemplar-screenshot-capture` CLI capabilities supply motion/interaction data, AI-generated imagery, and reference screenshots to the reference set. `load-references` loads all four reference-set layers before art-direction begins. The module's `/rbtv-strategist` command enters the loop and opens the Strategist for beat 1. Vivian PROACTIVELY proposes imagery via `image-gen` wherever an image strengthens the artifact — owner-gated, guided by the craft companion at `studio/capabilities/image-gen/image-craft.md`.

The **critic** (`studio/critic/`) is the optional improver: on demand (or when `critic: on` in design-state), it compares artifact variants via a taxonomy-cited structural pass and a separate advisory-to-human aesthetic section — never gates, never scores, never replaces the human gate or fresh-eyes.

**Folder layout note:** `standards/` is the module's shared cross-cutting reference data; `critic/` and `capabilities/` are content-named component folders (procedure/capabilities + co-located data) — per the Content-named folders convention in `component-patterns.md`.
