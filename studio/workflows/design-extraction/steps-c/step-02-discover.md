---
stepNumber: 2
stepName: 'discover'
nextStepFile: ./step-03-capture-extract.md
playwrightSkill: 'rbtv-playwright-cli'
---

# Step 02: Site Discovery

**Progress: Step 2 of 5** — Next: Capture & DOM Extraction

---

## STEP GOAL

Navigate the target website with Playwright, map its structure (pages, sections, interactive states), and produce a confirmed list of pages to capture in step-03.

---

## MANDATORY EXECUTION RULES

### Universal Rules

- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement

You are a Design System Analyst. Explore the site methodically — understand its structure before capturing anything.

### Step-Specific Rules

- Navigate with Playwright — do not rely on guessing site structure
- Discover ALL main pages, not just the homepage
- Detect interactive states (modals, dropdowns, hover reveals, tab panels)
- Present findings to user before proceeding — they choose which pages to capture

---

## MANDATORY SEQUENCE

### 1. Navigate to Target URL

Using Playwright:

1. Navigate to the target URL from the output document frontmatter
2. Wait for page load (network idle)
3. Handle cookie consent banners or modals if they block content
4. Take a quick orientation screenshot (not the full-page capture — that happens in step-03)

### 2. Scan for Pages and Sections

Programmatically discover the site's structure:

| Source | How to Extract |
|--------|---------------|
| Navigation menus | Query `nav a`, `header a`, elements with role="navigation" |
| Footer links | Query `footer a` — often contains sitemap-like link groups |
| Internal hrefs | Collect all `<a>` hrefs on the same domain |
| Sitemap | Check `/sitemap.xml` if accessible |

Filter results:
- Keep only same-domain URLs (no external links)
- Deduplicate (normalize trailing slashes, remove anchors)
- Exclude obvious non-page links (mailto, tel, javascript:, #)

### 3. Detect Interactive States

Click through main navigation items and observe:
- Dropdown menus or mega-menus that reveal content
- Tab panels or accordion sections
- Modal triggers (buttons that open overlays)
- JS-driven page transitions (SPAs with client-side routing)

Record each interactive state that reveals visually distinct content.

### 4. Build Site Structure Summary

Compile findings into a structured summary:

```
Site Structure: {website-name}

Pages Found:
1. Homepage — {url}/
2. About — {url}/about
3. Portfolio — {url}/portfolio
4. Contact — {url}/contact
...

Interactive States:
- Navigation dropdown: reveals 3 sub-sections
- Gallery lightbox: opens on image click
...

Total: {N} pages + {M} interactive states
```

### 5. Present to User for Confirmation

Ask the user which pages to capture:

```
I found {N} pages and {M} interactive states.

Which pages should I capture and extract tokens from?

[A] All pages (recommended for comprehensive extraction)
[S] Select specific pages (I'll list them for you to choose)
[H] Homepage only (minimal extraction)
```

HALT and wait for user selection.

If user selects [S], present the numbered list and let them pick.

### 6. Record Confirmed Page List

Write the confirmed page list to the output document body:

```markdown
## Confirmed Pages for Capture

| # | Page | URL | Notes |
|---|------|-----|-------|
| 1 | Homepage | {url}/ | |
| 2 | About | {url}/about | |
...
```

### 7. Update State

Add `step-02-discover.md` to `stepsCompleted` in output document frontmatter.

### 8. Present Menu Options

**Select an Option:**

- **[C] Continue** — Proceed to capture & DOM extraction (step-03)
- **[R] Re-explore** — Navigate the site again, look for missed pages
- **[X] Exit Workflow** — Save current state, exit

ALWAYS halt and wait for user selection.

---

## EDGE CASES

| Scenario | Action |
|----------|--------|
| SPA with client-side routing | Click navigation links, wait for content change, record each route as a page |
| Single-page site (no navigation) | Treat as one page with multiple sections. Scroll through and identify section anchors |
| Site requires authentication | Report to user. Ask if they can provide logged-in session cookies or skip protected pages |
| Site blocks automation | Report to user. Suggest manual screenshot upload as fallback |

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:

1. Ensure frontmatter is updated with `step-02-discover.md` in `stepsCompleted`
2. Load `./step-03-capture-extract.md` and follow its instructions

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:**
- Site navigated and structure mapped
- All main pages and interactive states identified
- User confirmed which pages to capture
- Confirmed page list written to output document

❌ **FAILURE:**
- Guessing site structure without navigating
- Capturing only the homepage without discovery
- Proceeding without user confirmation of page list
