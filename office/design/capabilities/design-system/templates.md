# design-system skill — file templates

Six scaffold files. Fill `{placeholders}`. Every rule is **assertion + WHY**. A rule is **law** unless marked `> [PROPOSED — pending owner ruling]`. Proposed items must not be applied as if ruled.

<!-- Filling agent: copy each fenced body into the named file. Do not copy this preamble. Instance values (hues, kinds, components, breakpoints) come from the project's interview/rulings — never from another product's system. -->

## Template: design-system.md

<!-- Core. Binding on every surface this system governs. Principles + tokens + interaction/state/copy + enforcement. View-only rules do not live here. -->

````markdown
# {project} design system — core

Agent-facing. Binding on every {surface} this system governs. Read this file plus `components.md` before any design change; also read `patterns.md` when composing a page, and `views/{view}.md` for the view being edited.

<!-- WHY a file split: one file cannot be both the token law and the per-family recipe and the per-view remainder. Agents load what the change touches. -->

| File | Rules on |
|---|---|
| `design-system.md` (this file) | Principles, tokens, type, space, radius, elevation, layout, interaction, states, copy, enforcement |
| `components.md` | Per-family recipes (markup, variants, states, do/don't) |
| `patterns.md` | Cross-view compositions (fold/collapse, trigger→popover, page archetypes) |
| `views/` | Per-view composition (hierarchy, view-only rules, known gaps) |
| `CLAUDE.md` | When to load this system, placement rule, required-view-sections, two-way door, self-check |
| `changelog.md` | Dated system-changes and exceptions, exceptions-in-force table |

Every rule below is a testable assertion plus a one-line WHY.

---

## 1. Principles

<!-- Fill only principles the owner has ruled. Drop any that only made sense for another product. Number them P1…Pn. Each is assertion + WHY. -->

**P1. Decoration is banned.** A color, bar, shadow, or radius that names nothing does not appear. WHY: unused chrome trains the reader to ignore the chrome that does name something.

**P2. One home per concept.** A finding, a kind, a control, a fact has exactly one surface. WHY: a second home splits attention and invents a second visual language.

**P3. One meaning per color.** A hue belongs to exactly one of the layers in §2. WHY: reuse across layers makes the legend unlearnable.

**P4. Words over color.** Labels, counts, and state names are written; color confirms. WHY: color-only meaning fails when the reader cannot see the hue.

**P{n}. {principle}.** {assertion}. WHY: {why}.

---

## 2. Color — disjoint layers

<!-- N meaning-layers that share no hex, plus a neutral surface/ink set that is NOT a meaning layer. Typical split: kind / status / interaction. Hexes are FORMAT examples; `:root` is the value source (§11). -->

A color names WHAT a thing is, everywhere it appears. The palettes do not share a hex.

### 2.1 Surfaces and ink (neutral; not a meaning layer)

| Token | Hex | When to use |
|---|---|---|
| `--bg` | `{#rrggbb}` | Page ground, recessed wells |
| `--surface` | `{#rrggbb}` | Raised reading surfaces |
| `--hair` | `{#rrggbb}` | Structural 1px edge |
| `--ink` | `{#rrggbb}` | Primary text |
| `--ink2` | `{#rrggbb}` | Secondary text |
| `--dim` | `{#rrggbb}` | Tertiary text |

**Assertion:** one hex per meaning; a second hex for the same meaning is an accident, not a variant. WHY: two hexes for one meaning is two legends.

### 2.2 Kind layer — {hue family} — global constants

<!-- Kind = stable identity. Same kind, same hue, every view. Token set shape: ink / wash / line / border. Status hues off-limits to kinds. New kinds via the two-way door. -->

| Kind | Ink | Wash | Line | Border | Token prefix |
|---|---|---|---|---|---|
| `{kind}` | `{#rrggbb}` | `{#rrggbb}` | `{#rrggbb}` | `{#rrggbb}` | `--k-{kind}` |

**Assertion:** `{kind}` is stable per entity (the table above). Navigability is view-declared: the view spec says which kinds are destinations here. Entities not in the table stay neutral (`--ink2` / `--hair`). A destination without a kind hue is pointer-cursor only — no new color. WHY: hue answers "what is this"; clickability answers "can this view open it".

### 2.3 Status layer

| Token | Hex | Meaning |
|---|---|---|
| `--bad` / `--bad-wash` | `{#rrggbb}` / `{#rrggbb}` | {worst level — e.g. broken / failing} |
| `--warn` / `--warn-wash` | `{#rrggbb}` / `{#rrggbb}` | {middle level — e.g. degraded / incomplete} |
| `--good` / `--good-wash` | `{#rrggbb}` / `{#rrggbb}` | {where good is allowed — keep scarce, or drop the token} |

**Assertion:** absence of color is the normal healthy state unless the owner has named the surfaces that may wear `--good`. WHY: painting "fine" in the positive hue makes real problems quieter.

### 2.4 Interaction layer

| Token | Hex | Meaning |
|---|---|---|
| `--accent` / `--accent-wash` | `{#rrggbb}` / `{#rrggbb}` | "You can act on this" and nothing else: selected filter, active tab, buttons, expand, focus |

**Assertion:** clickable kind-colored items wear the kind token, not `--accent`. WHY: clickability there is cursor + hover wash; accent would steal the kind.

**Assertion:** `{--ink2}` and `{--dim}` meet 4.5:1 contrast against `--surface`/`--bg` at the smallest type role; raise the failing token if a measurement fails. WHY: the smallest text fails contrast first.

### 2.5 Status contract

Shared interface. Views map source fields onto these levels; they do not invent new ones.

| Level | Token | Means |
|---|---|---|
| bad | `--bad` | {worst level meaning} |
| warn | `--warn` | {middle level meaning} |
| good | `--good` | {owner-named surfaces only} |
| neutral | (no color) | Normal; absence of status color |

**Assertion:** `{data producer}` computes status; the page only renders it. Pages never invent a status value. WHY: two pages computing the same entity differently is two homes for one fact (P2).

**Assertion:** status always carries a WORD. Color confirms. WHY: P4.

**Assertion:** precedence is bad > warn > good > neutral. A mixed item shows the worst level that applies. `good` is eligible only when no bad and no warn apply. WHY: a positive seal next to a defect is two answers.

**Assertion:** `kind` (stable, §2.2) is not status and is not navigability. WHY: one channel per question.

---

## 3. Type — {n} roles

**Assertion:** hierarchy comes from size, weight, letter-spacing and caps. {webfont ruling}. WHY: {why}.

Stack: `{font-stack}`. Mono: `{mono-stack}`.

| Role | Size | Weight | Token(s) | Used for |
|---|---|---|---|---|
| `{role}` | `{size}` | `{weight}` | `--fs-{role}` | `{used for}` |

<!-- Proven shape: five roles (display / section / body / label / micro). Legacy names map onto these — they are not extra sizes. -->

**Assertion:** do not add a size outside the table. WHY: a sixth role reopens the scale the interview closed.

---

## 4. Spacing

**Assertion:** a `{n}px` scale, consumed via tokens, governs **layout** spacing — gaps between blocks, section and container padding, page gutters. A layout gap set as a bare literal is an accident. WHY: extra steps at layout scale are how one-offs spread.

**Assertion (density exception):** control-INTERNAL paddings and optical offsets are **density values, not layout spacing**, and are lawful as literals where §4.1 or a component recipe states them. WHY: forcing every optical pad onto the scale changes how much the operator can see at once, which is the thing the scale exists to protect. Scope limit: this licenses tuning inside a control, never a layout gap.

| Token | Value | When to use |
|---|---|---|
| `--s-1` | `{4px}` | Tight intra-control, hairline insets |
| `--s-2` | `{8px}` | Inner control padding, compact gaps |
| `--s-{n}` | `{value}` | `{when}` |

**Assertion:** inside a component, space is even; between ranked regions, space is the default gutter, not a second box. WHY: extra boxes around ranked regions flatten the hierarchy.

### 4.1 Density

**Assertion:** {row height, control paddings} are the density literals §4 licenses — not a mobile-app minimum touch target unless this product is one. WHY: {who reads this, at what distance, and what density protects}.

---

## 5. Radius — {semantic}

**Assertion:** radius names {the semantic — e.g. whether the reader can act}, not how round something looks.

| Token | Value | Means | Used on |
|---|---|---|---|
| `--radius` | `{8px}` | Surface / container | {band, panel, card, popover} |
| `--radius-sm` | `{6px}` | You can click it | {buttons, search, filters} |
| `--radius-pill` | `{999px}` | Inert data | {chips, tags, counts} |

**Assertion:** no other radius values. WHY: a fourth radius is decoration (P1).

---

## 6. Elevation

**Assertion:** the default surface is flat ({surface} / hairline). Shadows are not decoration.

| Token | Value | Means |
|---|---|---|
| `--shadow-pop` | `{shadow}` | The floating-layer shadow (popovers, overlays) |
| `--ring` | `{shadow}` | Interaction ring, not depth (selected) |
| `--shadow-{name}` | `{shadow}` | {one named use — do not mint a shadow that means "looks lifted"} |

**Assertion:** chrome and reading surfaces get no shadow unless named above. WHY: shadows mark exactly the things in the table — nothing else.

---

## 7. Layout

**Assertion:** the shell is `{grid / layout formula}` with `{token}: {value}`. WHY: {what the columns are for}.

<!-- Named breakpoints only. Page rank order lives in patterns.md. -->

| Token | Value | When |
|---|---|---|
| `--{layout-token}` | `{value}` | `{when}` |

**Assertion:** `{bp-1}`, `{bp-2}`, `{bp-3}` are the only allowed media queries. WHY: named breakpoints prevent a new one-off from creeping in per component.

---

## 8. Interaction

**Assertion:** `{--accent}` is the only interaction color. WHY: §2.4.

**Assertion:** focus-visible is `{outline formula}` on `button`, `input`, and `[tabindex]`. WHY: keyboard path must be as visible as the pointer path.

**Assertion:** a fold uses `aria-expanded`, a durable `state.open` key, and resets when the reader leaves the item. Absent key = the default stated in the view spec. WHY: a fold that forgets its contract reopens or stays shut at random.

**Assertion:** tab order follows visual order: `{region} → {region} → {region}`. WHY: a keyboard path that skips a visible region is a hidden control.

**Assertion:** a popover closes on `Escape` and returns focus to its trigger. `role="dialog"` requires `aria-labelledby` pointing at the popover heading. WHY: a close that dumps focus, or a dialog with no name, strands a keyboard or screen-reader.

**Assertion:** page verbs are text controls in `--accent`, not filled buttons. Transitions use `--dur-fast: {ms}` or `--dur-{name}: {ms}` only; `prefers-reduced-motion` turns them off; layout is never animated. Icons are `{format, size}`; emoji-as-icon is banned; icon-only requires `aria-label`. WHY: extra durations and unnamed icons are decoration or defects.

---

## 9. States

| State | Assertion | WHY |
|---|---|---|
| Empty | Named variants in `components.md` (at least: no-data, zero-items, filtered-no-results, failed-load). Each names the cause and the recovery. Render nothing when absence is the healthy default. | A single "none" sentence cannot tell those cases apart. |
| Error | One home for broken-as-defined, using the status contract. Never a second error surface. | P2. |
| Overflow | Clamp + fade + a text "Show more"; names ellipsize. | Air, not a scrollbar inside a section. |
| Loading | Preserve the expected layout with static placeholders at body size — no spinner. | A spinner shifts the page and is a sixth accent. |

---

## 10. Copy

**Assertion:** labels lead with words. A control's name is its text, not its color. Micro-caps are only for `{label-like surfaces}`. Section titles are the words as authored, not caps. Identity facts are a quiet meta line (dim label, colon, value) — never pills. Buttons and folds are sentence case, verb-first. WHY: P4; if everything shouts, nothing is a label.

**Assertion:** an error or finding message leads with a word, names the object, and states the consequence. Counts `{format}`, paths `{format}`, dates `{YYYY-MM-DD or ruled form}` — one format per data type, taken from what is already on screen. WHY: a reader scanning by word must get the same information a reader scanning by color gets.

---

## 11. Enforcement

**Assertion:** no component CSS may contain a literal color, spacing, radius, or duration — only `var(--token)`. New values are new tokens, which are a system change (`CLAUDE.md`). WHY: literals are how one-offs spread.

**Assertion:** a new token, component, or kind is not added because one screen wants it. It must be needed by more than one view, or it is a view-local exception logged in `changelog.md`. Before adding one, check whether an existing token or component already does the job. WHY: one-screen tokens are decoration with a name; a duplicate token is a second home for the same fact (P2).

**Assertion:** the page's own `:root` CSS custom-properties block is the authoritative source of every token value. The tables in these files are documentation of that block, not a second source — if they ever disagree, `:root` wins and the table is stale and must be corrected. WHY: one source of truth; a markdown table cannot enforce itself at runtime.

**Assertion:** token names are semantic (they say WHY a value is used, not what it looks like) in the shape `category-concept-property-state` with state last, e.g. `--k-{kind}-wash`, `--warn-bord`, `--btn-hover`. WHY: a name that describes the pixel (`--blue-2`) breaks the moment the pixel changes for a reason unrelated to its name.

**Self-check** (required in the done report): every value used is an existing token; no new one-off literals; principles and layer rules respected. Run it, don't just attest: grep the changed CSS for literal hex codes and bare `px` values outside the `:root` block. A literal hex is always a violation. A bare `px` is a violation when it sets **layout** spacing; a control-internal padding or optical offset is a lawful density value under §4.
````

## Template: components.md

<!-- Per-family recipe cards. One card per family that exists in the HTML. Do not invent a class that is not here. A blank section is a gap — every heading is filled, with `not applicable` when that is the ruling. Fold-capable families follow the fold/collapse contract in patterns.md. -->

````markdown
# {project} components

Recipes for families in the current {surface}. Markup is the copyable shape; CSS is tokenized from the implementation. Do not invent a class that is not here. A blank section is a gap — every heading is filled, with `not applicable` when that is the ruling.

Required sections, in this order: **Purpose** · **Anatomy** · **Markup + CSS** · **Variants** · **States** · **Accessibility** · **Do / Don't** · **Tokens used**.

<!-- WHY this order: purpose before anatomy (not a class dump); markup before variants (one copyable shape); states and a11y cannot be skipped; tokens close the card. -->

Fold-capable families follow the fold/collapse contract in `patterns.md`.

---

## {Family name}

**Purpose.** {one job this family does, and what it must not out-shout}.

**Anatomy.** {surface class} → {child} → {child}. {slots that appear only in some states}.

**Markup + CSS.**

```html
<!-- Minimal copyable shape. Tokenized. No instance content. -->
<div class="{family}">…</div>
```

```css
.{family}{background:var(--{token});border-radius:var(--radius)}
```

**Variants.** {named variants, or `not applicable — one shape`}. Hue/word is the difference; anatomy is not.

**States.** {rest / hover / open / absent / clamped / …}. Loading / empty / error / overflow: each named, or `not applicable`. A fully empty healthy default renders nothing, not a hollow box.

**Accessibility.** {heading level or button; aria-* the trigger carries; the WORD that carries meaning when color is gone; focus ring; inert vs in tab order}. Icon-only requires `aria-label`.

**Do / Don't.** Do {the one thing that keeps the family's job}. Don't {the failure that would split a home, steal a hue, or decorate}.

**Tokens used.** `--{token}`, `--{token}`.

---

<!-- One card per family that exists. If a family looks reusable for a different job (graph node vs collection row vs index row), say so under Purpose and name the other family — do not stretch one class across three jobs. -->
````

## Template: patterns.md

<!-- Cross-view compositions only. A pattern is promoted here only once a second view actually needs it. One-view need stays in views/{view}.md. -->

````markdown
# {project} patterns

Compositions that recur across more than one view — how components are put together, not the components themselves (`components.md`) or a single view's own layout (`views/{view}.md`). A view file states which pattern it uses and its view-specific values; it does not restate the mechanics here.

**Assertion:** a pattern is promoted here only once a second view actually needs it (or plainly will). Do not add a pattern for a one-view need — that stays in the view file (see `CLAUDE.md`'s placement rule). WHY: promoting later is cheap; demoting a wrongly-promoted rule is not.

---

## Fold / collapse contract

**Where used.** {families that collapse and re-expand}.

**Assertion:** every fold uses `aria-expanded` on its trigger, a durable `state.open[key]` entry, and restores focus via `{focus-key}` when the surrounding content re-renders. Absent key = the view's stated default (usually collapsed). The fold resets to its default when the reader leaves the item it belongs to. WHY: a fold that forgets its own state reopens or stays shut at random, and a re-render that drops focus silently strands a keyboard reader.

---

## Trigger → popover contract

**Where used.** {each popover and its trigger}. Any future icon-only control that opens a floating panel.

**Assertion:** the trigger is a `button` carrying `aria-expanded` and `aria-label` (icon-only controls have no visible text); the popover it opens is `position:absolute`, anchored to the trigger, `role="dialog"` with `aria-labelledby` pointing at its heading, and closes on outside click and on `Escape` — Escape returns focus to the trigger. Only one popover is open at a time. WHY: one open/close mechanism means a reader who has learned one popover has learned all of them.

---

## Page archetypes

<!-- Drop an archetype the product does not have. Do not invent a fourth until a second view needs it. -->

Three shapes. A view file names which one it is and which of its components fill each rank — it does not redefine the ranks.

### Item-detail page

**Where used.** Any page that shows one entity's full detail.

**Assertion:** rank is fixed — **1. Identity** (name, facts, description; the one apex surface) → **2. Findings** (everything wrong, directly under identity) → **3. Corpus** (the page's main activity) → **4. Rail** (secondary/reference, visibly subordinate) → **Chrome** (neutral, ranked outside the content order). WHY: one apex per page; ranking by position is how the reader learns what matters most without re-reading labels every time.

**Assertion:** the rail never regains corpus rank, and findings never split across two homes. WHY: promoting the rail or splitting findings flattens the one hierarchy the page teaches.

**Composed of.** {identity family, findings family, corpus family, rail family, chrome families}.

### Collection page

**Where used.** Any page whose main activity is a list of entities.

**Assertion:** rank is **Chrome** → **List** (entity rows; this is the corpus) → **Empty** (the matching empty-state variant). No identity band (the band is one item's apex). No rail by default. WHY: a list of many things has no single apex; putting a band on it would shout a name that is not the subject.

**Composed of.** {chrome, entity row, empty state, search/filters}.

### Graph page

**Where used.** Any page whose main activity is a graph of nodes and edges.

**Assertion:** rank is **1. Identity** (the graph's subject) → **2. Findings** → **3. Graph** (nodes; this is the corpus) → **4. Rail** (optional) → **Chrome**. WHY: the graph is the activity, not an appendix.

**Composed of.** {identity family, findings family, graph-node family, chrome}. Entity-row is not this page.
````

## Template: views/{view}.md

<!-- One file per view. Created in the same turn the view is built. Not complete until all five required sections are stated — "not applicable" is valid; silence is not. View-only rules stay here; do not put them in design-system.md. -->

````markdown
# View spec — {view}

Composition rules for the {view} view. Core tokens and component recipes live in `design-system.md` and `components.md`. Cross-view compositions live in `patterns.md` — read it alongside this file. This file is the {view}-specific remainder.

<!-- WHY: core cannot hold per-view hierarchy. These five sections are the contract so a later agent does not invent data, status, or states. -->

---

## Archetype and rank

Follows the `{item-detail | collection | graph}` page rank order in `patterns.md`. {view} fills each rank as:

| Rank (from `patterns.md`) | {view} component | Treatment |
|---|---|---|
| {rank} | {component family} | {how this view treats it — apex, one home, appendix, neutral chrome} |

**Assertion:** {any view-local rank rule, e.g. findings have one home}. WHY: {why}.

---

## 1. Data shape

**Assertion:** this view reads, per entity: `{field}` (from `{source}`), `{field}` (from `{source}`). It does not read `{out-of-scope fields}`. WHY: a view that silently grows its data shape invents a second producer.

<!-- List every field. "Where they come from" is the producer (API, generator, file) — not a CSS class. -->

---

## 2. Status derivation

**Assertion:** `{producer}` computes status; this page only renders it. Mapping onto the core status contract (`design-system.md` §2.5):

| View field / condition | Level |
|---|---|
| `{field or condition}` | bad / warn / good / neutral |

Do not invent a level. WHY: two pages computing the same entity differently is two homes for one fact.

---

## 3. States

Every state named in core §9 has a row (even "not applicable"):

| Core state | This view | Maps to |
|---|---|---|
| Empty | {which empty-state variant, or render nothing} | `components.md` empty-state / {family} |
| Error | {the one error home} | findings family / {family} |
| Overflow | {clamp, ellipsis, or n/a} | fold contract / {family} |
| Loading | {placeholders, or n/a} | core §9 |

---

## 4. Interaction

What the reader can click / expand / filter, and which `patterns.md` contract each follows:

| Control | Does | Pattern |
|---|---|---|
| `{control}` | `{does}` | fold / collapse · trigger → popover · {other} |

**Completion check:** every interactive element cites the `patterns.md` contract it follows.

---

## 5. Responsive

Behavior at the breakpoints named in `design-system.md` §7:

| Breakpoint | This view |
|---|---|
| `{bp-1}` | `{what stacks / overlays / insets}` |
| `{bp-2}` | `{…}` |
| `{bp-3}` | `{…}` |

---

## Known gaps

| Gap | What it is | Status |
|---|---|---|
| `{gap}` | `{what}` | `{owed / out of scope / do not spread}` |

<!-- Optional. Gaps are not rules. Do not revive a dropped variant from this table. -->
````

## Template: CLAUDE.md

<!-- Governance, not tokens. When to load which file, where a rule belongs, what to do on contradiction, what "done" means. Drop any skill-invocation mandate that is not this system's own. -->

````markdown
# {project} — design-system governance

Applies to any agent editing {surface} this system governs. Does not bind other products.

## Before any design change

1. Read `design-system.md` and `components.md`.
2. Read `patterns.md` when composing a page — it holds compositions that recur across more than one view. A view file states which pattern it uses; it does not restate the mechanics.
3. Read the relevant `views/{view}.md`. If the view has no file yet, stop and create it in the same turn you build the view — see "New views" and the required-sections template below.

<!-- WHY load-order: tokens first (no one-off); patterns before the view (no restated mechanics); view last (hierarchy applied, not redesigned). -->

## Where a composition rule belongs

A one-view-only composition need is not automatically a system change. Decide with this rule: composition that is local to how one view arranges its own components stays in that view's `views/{view}.md`. Behavior meant to be reused by more than one view belongs in core (`components.md` for a component, `patterns.md` for a cross-view composition). A single-view need enters core (`patterns.md`) only if, while writing it, you can name it as a *general* pattern another view would plausibly reuse — not merely because it is well-written or reusable in principle. When in doubt, leave it in the view file; promoting later is cheap, demoting a wrongly-promoted rule is not.

## Two-way door on contradictions

If a request conflicts with the system, **stop and ask the owner**. Do not silently deviate.

Options to present:

- **(a) One-off exception** — do the requested thing this once, and log it in `changelog.md` as `type: exception` (where, why, what migrates or expires).
- **(b) System change** — update the system files in the same turn, then do the work, and log it in `changelog.md` as `type: system-change`.

Never invent a third path. An unlogged deviation is a defect.

## Keep the system current

When a change is approved, update the system files in **the same turn**. Chat must not hold a rule the files do not.

A new token, component family, kind, or view-level composition rule is a system change, not a local CSS edit.

## Self-check (required in the done report)

Before reporting done, state all three:

1. Every value used is an existing token.
2. No new one-off literals were introduced.
3. Principles, color layers, radius, and the view spec were respected.

If any check fails, fix or log an exception — do not report done.

## New views

When a view is built, create `views/{view}.md` in the same turn. Do not put view-only rules in `design-system.md`.

### Required sections for `views/{view}.md`

A view file is not complete until it states all five, even briefly ("not applicable" is a valid answer, silence is not):

1. **Data shape** — what fields the view reads per entity, and where they come from.
2. **Status derivation** — how each entity's status (or equivalent state) is computed and who owns that computation. Must use the core status contract (`design-system.md` §2.5): map view fields onto bad / warn / good / neutral; do not invent a level. `{producer}` computes; the page renders.
3. **States** — every state the view's content can be in (empty, error, overflow, loading, etc.), each mapped to the matching row in `design-system.md` §9.
4. **Interaction** — what the reader can click/expand/filter, and which pattern from `patterns.md` each interaction follows.
5. **Responsive** — behavior at the breakpoints named in `design-system.md` §7.

**Completion check:** before calling the view file done, confirm every state named in core §9 has an entry above (even "not applicable"), and every interactive element cites the `patterns.md` contract it follows. A view file that skips a section silently is incomplete, not minimal.
````

## Template: changelog.md

<!-- Written in the same turn as any system-change or exception. Newest first. An unlogged deviation is a defect (CLAUDE.md). -->

````markdown
# Design-system changelog

Written in the same turn as any system-change or exception. Newest first.

## Exceptions in force

<!-- Standing exceptions only — not expired ones, not system-changes. Empty table is valid (header in, no rows). -->

| rule broken | where | why | since |
|---|---|---|---|
| {rule, with section} | `{where — class or view}` | {why this is not a fix owed} | `{YYYY-MM-DD}` |

## Log

| date | change | type | rationale |
|---|---|---|---|
| `{YYYY-MM-DD}` | {what changed, in one sentence, with file names} | `system-change` \| `exception` | {why, in one sentence} |

## Format

| column | meaning |
|---|---|
| date | `YYYY-MM-DD` |
| change | What changed, in one sentence, with file names |
| type | `system-change` (rule/token/component updated globally) or `exception` (logged one-off; say where and what expires) |
| rationale | Why, in one sentence |

Flag a **semantic** token change (the meaning of a token changed, not only its hex) in the change cell. A changelog line is not enough on its own for that case — the two-way door in `CLAUDE.md` still applies.
````
