---
title: 'Compound: Pitch Deck HTML Generation Lacks PDF Page-Break Validation and Asset Sizing Constraints'
docType: 'compound'
mode: 'create'
priority: 'High'
tracker: ''
stepsCompleted: ['step-01-init.md', 'step-02-self-assessment.md', 'step-03-discussion.md', 'step-04-document.md']
inputDocuments:
  - '_bmad/rbtv/workflows/pitch/steps-c/step-07-generate.md'
  - '_bmad/rbtv/workflows/_shared/pitch-data/html-patterns.md'
  - '_bmad/rbtv/workflows/_shared/pitch-data/html-components.md'
outputPath: '_bmad/rbtv/_admin/roadmap/todos/_claude-code-workspace/pitch-workflow'
date: '2026-03-17'
yoloMode: false
---

# Pitch Deck HTML Generation Lacks PDF Page-Break Validation and Asset Sizing Constraints

**Type:** Workflow + System File
**Priority:** High
**Tracker:**
**Status:** Backlog

---

## Overview

### Problem

The pitch deck generation workflow (step-07-generate) produces HTML that repeatedly breaks across PDF page boundaries when exported via Ctrl+P. During the Tecer × ContabExpress proposal session, slides 4 and 11 both overflowed to a second page, requiring manual CSS overrides. Additionally, logo sizing required 4 rounds of user correction (40px → 64px → 100px → 160px), logo color inversion for dark backgrounds was missed entirely, and background textures were applied too aggressively — all problems the workflow could have prevented with explicit constraints.

### Goals

1. HTML slides must fit within a single landscape page on PDF export — validated before delivery
2. Logo handling (sizing, color inversion, multi-logo composition) must have explicit patterns
3. Background image usage must have subtlety constraints
4. The generation step must include a self-check that catches overflow before presenting to user

### Constraints

- Cannot add browser-based validation without Playwright MCP availability (unreliable in current setup)
- Must work within the existing step-07-generate workflow structure
- Patterns must be generic enough for both client and investor decks
- Cannot enforce pixel-perfect PDF rendering across all browsers — constraints must be defensive

---

## Self-Assessment

### Error Analysis

**Error type:** Knowledge gap + Execution failure

**Expectation vs. actual:**
- User expected: A pitch deck that exports cleanly to PDF via Ctrl+P with no visual issues
- Actual: 3 slides broke across pages, logo was invisible on dark bg, background textures overwhelmed content, logo sizing required 4 correction rounds

**Impact:** Multiple iteration cycles wasted context window and user time. The issues are systematic — they'll recur on every pitch deck generation until the patterns and workflow are updated.

**Root causes:**
1. `html-patterns.md` provides `padding-bottom: calc(60px + 10vh)` for optical centering but has NO constraint linking content height to viewport bounds. Dense slides (process diagrams, closing with photos) exceed the available space after padding.
2. `step-07-generate.md` has a "Verify Output" checklist that checks for page breaks but only verifies `page-break-after: always` CSS property exists — not whether content actually fits within one page.
3. No logo component pattern exists in `html-components.md`. The agent improvised logo handling with no guidance on sizing proportionality, color inversion for dark backgrounds, or multi-logo composition.
4. No background image subtlety constraints exist. The agent applied textures to 5 slides simultaneously without testing visual impact.

### Context Source Evaluation

| File | Loaded? | Issue |
|------|---------|-------|
| `workflows/pitch/steps-c/step-07-generate.md` | Yes | Verification checklist checks CSS properties exist but not whether content fits within page bounds. No logo handling guidance. |
| `workflows/_shared/pitch-data/html-patterns.md` | Yes | 12 design constraints, none about content overflow. Padding pattern `calc(60px + 10vh)` actively causes overflow on dense slides. No logo patterns. |
| `workflows/_shared/pitch-data/html-components.md` | Yes | Missing: logo component, background image component. Agent improvised both. |
| `brand/assets/presentations/manifest.md` | Yes | Lists assets but doesn't document color handling (dark/light bg inversion). |
| `_clients/contab/assets/manifest.md` | Did not exist | Created during session. |

### Improvement Options

1. **New Rule**: Content-height estimation constraint before rendering
   - **Rationale:** Force the agent to estimate content height vs viewport before rendering. Dense slides must use `flex-start` with reduced padding.
   - **Location:** New constraint rows in `html-patterns.md`
   - **Pattern Consistency:** Follows existing constraint table format

2. **Modify Existing Rule**: Add logo + background image pattern sections to `html-patterns.md`
   - **Rationale:** Logos and background images are as common as icons — they need explicit patterns
   - **Location:** Two new sections in `html-patterns.md`
   - **Pattern Consistency:** Follows existing section structure (header → CSS → guidance)

3. **Update System File**: Add content-fit check to step-07-generate verification table
   - **Rationale:** Existing verification checks CSS exists but not whether content fits
   - **Location:** `step-07-generate.md` verification table
   - **Pattern Consistency:** Adds rows to existing table

4. **Add Constraint**: Logo sizing proportionality and color inversion rules
   - **Rationale:** Prevents multi-round sizing corrections and invisible logos on dark backgrounds
   - **Location:** `html-patterns.md` constraints table + logo pattern section
   - **Pattern Consistency:** Follows constraint table format

5. **Alternative Approach**: Post-generation validation micro-step (step-07b)
   - **Rationale:** Dedicated validation step between generate and images
   - **Location:** New file `step-07b-validate.md`
   - **Pattern Consistency:** Breaks step numbering but architecturally sound

---

## Proposed Solution

Implement options 2, 3, and 4 as a combined scope — they modify two existing files without creating new files or breaking step numbering.

### Change 1: Logo Pattern section in `html-patterns.md`

Add after the existing "## Icon Libraries" section:

```markdown
## Logo Pattern

### Single Logo (Cover/Closing)

​```css
.cover-wordmark {
  height: clamp(40px, 6vh, 80px);
  filter: brightness(0) invert(1); /* renders white on dark backgrounds */
}
​```

- Cover/closing logo height: 5-8% of viewport height (`clamp(40px, 6vh, 80px)`)
- Dark backgrounds: ALWAYS apply `filter: brightness(0) invert(1)` to non-white logos
- Light backgrounds: use logo as-is (no filter)
- `onerror="this.style.display='none'"` on all logo img tags

### Multi-Logo Composition

​```css
.cover-logos {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: clamp(20px, 3vw, 40px);
}
​```

- Logos with more visual mass (icon + text) should be sized 10-20% smaller in height than simpler wordmarks to achieve visual balance
- Separator between logos: `×` character, font-weight 300, opacity 0.5-0.6
- ALWAYS test multi-logo compositions at the actual slide size — aspect ratio differences cause surprises

### Asset Manifest Color Handling

When creating or reading asset manifests (`manifest.md`), document whether each logo/asset is dark-on-transparent or light-on-transparent. Include the CSS filter instruction for dark bg usage.
```

### Change 2: Background Image Pattern section in `html-patterns.md`

Add after the new Logo Pattern section:

```markdown
## Background Image Pattern

​```css
.slide--textured {
  background-color: var(--fallback-color);
  background-image: url('images/texture.png');
  background-size: cover;
  background-position: center;
}
​```

| Constraint | Rule |
|---|---|
| Max textured slides | Max 3 textured backgrounds per deck (cover, closing, and 1 accent). Remaining slides use flat colors. |
| Fallback color | ALWAYS set `background-color` as fallback before `background-image` |
| Subtlety test | If the texture competes with text readability, mute it with a semi-transparent overlay: `background-image: linear-gradient(rgba(R,G,B,0.7), rgba(R,G,B,0.7)), url(...)` |
| Print rendering | Background images require `print-color-adjust: exact` — already set globally but verify |
```

### Change 3: New constraint rows in `html-patterns.md` Design Constraints table

Add rows 13-16:

```markdown
| 13 | **Content overflow** | Slides with >3 content zones, process diagrams, or >4 bullet items must use `justify-content: flex-start` with `padding-top: 50px; padding-bottom: 40px;` instead of centered layout. Centered layout is only safe for sparse slides. |
| 14 | **Logo sizing** | Cover logo height: `clamp(40px, 6vh, 80px)`. Multi-logo: size by visual mass, not pixel height. Dark bg logos must use `filter: brightness(0) invert(1)`. |
| 15 | **Background texture limit** | Max 3 textured slides per deck. Never apply the same texture to more than 2 slides. |
| 16 | **Content-fit validation** | Before finalizing, estimate each slide's total content height. If title + subtitle + content block exceeds ~70vh, switch to top-aligned layout with reduced padding. |
```

### Change 4: Add verification row to `step-07-generate.md`

Add to the verification table in section "### 6. Verify Output":

```markdown
| Content fit | Every slide's content fits within one landscape page — dense slides use top-aligned layout |
| Logo rendering | Logos visible on their backgrounds (dark bg → white filter applied) |
```

### Implementation Details

| Aspect | Details |
|--------|---------|
| File(s) to modify | `_bmad/rbtv/workflows/_shared/pitch-data/html-patterns.md`, `_bmad/rbtv/workflows/pitch/steps-c/step-07-generate.md` |
| Scope of change | Moderate — adds 2 new sections + 4 constraint rows to patterns file, 2 verification rows to step-07 |
| Related files | `html-components.md` (may want a logo component entry), asset `manifest.md` files (should follow color handling guidance) |

---

## Rationale

These three changes address the root causes identified in the error analysis without introducing new files or breaking existing workflow structure:

- **Logo patterns** prevent the 4-round sizing correction loop and the invisible-logo-on-dark-bg error — the agent has explicit rules instead of improvising
- **Background texture constraints** prevent over-application (the "overwhelming" feedback happened because no limit existed)
- **Content-fit validation** catches page-break overflow before the user sees it — the most impactful single change since PDF export is the primary delivery format
- **All changes modify existing files** following their established structure — no new step files, no numbering changes

---

## Acceptance Criteria

- [ ] `html-patterns.md` contains "## Logo Pattern" section with single-logo, multi-logo, and color inversion guidance
- [ ] `html-patterns.md` contains "## Background Image Pattern" section with max-texture and subtlety constraints
- [ ] `html-patterns.md` Design Constraints table includes rows 13-16 (content overflow, logo sizing, texture limit, content-fit validation)
- [ ] `step-07-generate.md` verification table includes content-fit and logo-rendering checks
- [ ] A test pitch deck generation using the updated patterns produces no page-break overflow on first attempt

---

## Related Files

| File | Relationship |
|------|--------------|
| `_bmad/rbtv/workflows/_shared/pitch-data/html-patterns.md` | Primary target — receives logo, background, and constraint additions |
| `_bmad/rbtv/workflows/pitch/steps-c/step-07-generate.md` | Secondary target — verification table update |
| `_bmad/rbtv/workflows/_shared/pitch-data/html-components.md` | May want a logo component entry in the future |
| `projects/tecer-biz/brand/assets/presentations/manifest.md` | Should follow the new color handling guidance pattern |
| `projects/tecer-biz/_clients/contab/presentations/2026-03-17-proposal/pitch-deck.html` | Triggering artifact |

---

## References

- Triggering session: Tecer × ContabExpress proposal pitch deck generation (2026-03-17)
- Issues: PDF page-break overflow (slides 4, 11), logo sizing (4 rounds), logo color inversion (missed), background texture overwhelm (2 rounds)

---

## Discussion Notes

### Selected Improvement Option
Options 2 + 3 + 4 combined — logo/background patterns, content-fit constraints, and verification table updates.

### Implementation Preferences
- **File Location:** `html-patterns.md` and `step-07-generate.md` (existing files only)
- **Scope:** Moderate — two new sections, 4 constraint rows, 2 verification rows
- **Priority:** High

### Additional Context
User chose all three complementary options as a single implementation scope. No new files or step numbering changes — keeps the workflow structure intact.
