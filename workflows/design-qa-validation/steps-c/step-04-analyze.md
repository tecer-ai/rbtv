---
stepNumber: 4
stepName: 'analyze'
nextStepFile: null
---

# Step 04: 4-Layer Analysis

**Progress: Step 4 of 4** — Final Step

---

## STEP GOAL

Apply the 4-layer validation framework to all captured screenshots and produce the final validation report.

---

## MANDATORY EXECUTION RULES

### Universal Rules

- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement

You are a Design QA Specialist. Apply adversarial mindset — assume flaws exist and actively search for them.

### Step-Specific Rules

- Analyze EACH screenshot visually (not just text descriptions)
- Apply ALL 4 layers to EACH viewport
- Document specific locations, not vague observations
- Assign severity to every finding
- Compare to benchmark if provided

---

## MANDATORY SEQUENCE

### 1. Verify Screenshots in Context

Confirm all screenshots from step-03 are loaded:
- "Analyzing {N} screenshots across {M} viewport(s)"

If screenshots not in context, STOP and return to step-03.

### 2. Apply Layer 1: Structural Integrity

**Question:** Does it work?

For EACH screenshot, check:

| Check | What to Look For |
|-------|------------------|
| Resources | Images loaded, fonts rendering, CSS applied |
| Console | Errors from step-03 console check |
| Layout | No overflow, overlap, or broken grids |
| Responsive | Elements adapt correctly at each viewport |
| Images | Aspect ratios maintained, not pixelated |
| Interactive | Buttons/links properly sized for touch/click |

Document findings with severity (Critical/Major/Minor).

### 3. Apply Layer 2: Visual Hierarchy

**Question:** Can users navigate by eye?

For EACH screenshot, check:

| Check | What to Look For |
|-------|------------------|
| Eye flow | Clear path from most to least important |
| Focal points | One clear focal point per section |
| Emphasis | Important elements stand out (size/color/weight/space) |
| Grouping | Related items together, unrelated separated |
| Whitespace | Adequate breathing room |
| Sections | Clear boundaries between content areas |
| Text rhythm | Readable line-height and line-length |
| Reading pattern | Follows Z-pattern (scanning) or F-pattern (reading) |

Document findings with severity.

### 4. Apply Layer 3: Brand & Aesthetic Excellence

**Question:** Does it look professional?

For EACH screenshot, check:

| Check | What to Look For |
|-------|------------------|
| Design tokens | Colors, fonts, spacing consistent |
| Typography | Clear H1→H2→H3→body hierarchy |
| Color harmony | No clashing colors, proper contrast (WCAG AA) |
| Visual balance | Weight distributed appropriately |
| Polish | Consistent border-radius, shadows, alignment |
| Image quality | High resolution, not compressed artifacts |
| Brand personality | Style matches intended brand voice |
| Pattern consistency | Repeated patterns are identical |

Document findings with severity.

### 5. Apply Layer 4: UX & Communication

**Question:** Does it serve its purpose?

For EACH screenshot, check:

| Check | What to Look For |
|-------|------------------|
| Message clarity | Core message clear within 3 seconds |
| CTA visibility | Primary call-to-action prominent |
| Scannability | Content easily scannable |
| Density | Not overwhelming, appropriate information density |
| Content hierarchy | Most important content most prominent |
| Narrative flow | Logical reading sequence |
| Accessibility | Contrast sufficient, font size ≥14px |
| Goal support | Design supports document's purpose |

Document findings with severity.

### 6. Benchmark Comparison (If Applicable)

If benchmark provided in step-01:

1. Load benchmark screenshots via `read_file`
2. Compare side-by-side at same viewport
3. Check alignment:
   - Key element positions match
   - Layout structure consistent
   - Visual tone aligned
   - Justified deviations documented

### 7. Determine Overall Status

| Status | Criteria |
|--------|----------|
| ✅ **Pass** | No Critical, ≤2 Major, Minor acceptable |
| ⚠️ **Issues** | No Critical, >2 Major or significant Minor accumulation |
| ❌ **Critical Failures** | Any Critical findings |

### 8. Generate Final Report

Compile findings into validation report:

```markdown
# Design Validation Report

**Document:** {filename}
**Type:** {document-type}
**Status:** {status-icon} {status}

## Summary
{1-2 sentence executive summary}

## Findings by Layer

### Layer 1: Structural Integrity
| Severity | Issue | Location | Impact |
|----------|-------|----------|--------|
{findings}

### Layer 2: Visual Hierarchy
| Severity | Issue | Location | Impact |
|----------|-------|----------|--------|
{findings}

### Layer 3: Brand & Aesthetic
| Severity | Issue | Location | Impact |
|----------|-------|----------|--------|
{findings}

### Layer 4: UX & Communication
| Severity | Issue | Location | Impact |
|----------|-------|----------|--------|
{findings}

## Benchmark Comparison
{alignment assessment or "No benchmark provided"}

## Recommendations
1. {Priority action}
2. {Secondary action}
3. {Additional recommendation}
```

### 9. Update State

Add `step-04-analyze.md` to `stepsCompleted` in output document frontmatter.
Update status field to final determination.

### 10. Present Menu Options

**Select an Option:**

- **[S] Save Report** — Save validation report to output directory
- **[R] Re-analyze** — Run analysis again with different focus
- **[F] Fix Issues** — Begin addressing identified issues
- **[X] Exit Workflow** — Complete workflow

ALWAYS halt and wait for user selection.

---

## SEVERITY DEFINITIONS

| Severity | Definition | Examples |
|----------|------------|----------|
| **Critical** | Blocks functionality or obscures message | Broken layout, missing images, unreadable text |
| **Major** | Significantly degrades UX or professionalism | Poor contrast, inconsistent spacing, weak hierarchy |
| **Minor** | Noticeable but doesn't prevent usage | Slight misalignment, minor color inconsistency |

---

## ADVERSARIAL MINDSET

- Assume flaws exist — search actively
- Check edge cases (long text, empty states)
- Consider diverse users (mobile, accessibility needs)
- Question every design decision
- Look for what's MISSING, not just what's wrong

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[S] Save Report** is selected:

1. Write final report to `{output_folder}/design-validation-{slug}.md`
2. Confirm save: "Validation report saved to {path}"
3. Offer next steps: "Would you like me to help fix any issues?"

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:**
- All 4 layers applied to all screenshots
- Specific findings with severity, location, impact
- Overall status determined
- Benchmark comparison (if applicable)
- Final report generated
- Menu presented with explicit HALT

❌ **FAILURE:**
- Skipping layers or viewports
- Vague observations without specifics
- Missing severity assignments
- Proceeding without analyzing all screenshots
