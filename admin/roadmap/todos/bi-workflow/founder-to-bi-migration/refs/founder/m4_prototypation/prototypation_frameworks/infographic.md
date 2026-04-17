---
---

# Infographic Creation Framework

**Purpose:** Execute systematic infographic creation using visual-first design principles to communicate complex information through data visualization, icons, and minimal text.

**Context:** Use in M4 Prototypation for data-rich visual documents. Produces scrollable, section-based HTML infographics.

---

## Framework Overview

Infographics reverse the hierarchy: visual elements carry the primary message while text provides minimal context. This task-based approach ensures rigorous execution from type selection through validation.

---

## Task Structure

High-level view of framework execution:

| Task | Goal | Key Inputs | Key Outputs |
|------|------|------------|-------------|
| 1. Define Infographic Purpose and Type | Select appropriate infographic pattern for content goals | Content to communicate, target audience | Infographic type selection, content goal statement |
| 2. Structure Content for Visual Communication | Organize information into scannable sections | Raw content, selected type | Section outline, content hierarchy |
| 3. Select Visual Elements and Data Visualizations | Choose icons, charts, colors, and visual patterns | Section outline, brand guidelines | Visual element specifications, color scheme |
| 4. Create Information Hierarchy | Establish visual priority from hero to supporting elements | Content structure, visual elements | Visual hierarchy specification |
| 5. Design Layout and Flow | Build section-based vertical scroll layout | All prior outputs | HTML/CSS implementation |
| 6. Validate Visual Clarity | Verify against design criteria and anti-patterns | Completed infographic | Validation checklist, revision list |

---

## Task 1: Define Infographic Purpose and Type

**Goal:** Determine communication objectives and select the appropriate infographic pattern that best supports those objectives.

**Inputs:** Content requiring visual communication

| Input | Source | Required |
|-------|--------|----------|
| Raw content or data | User knowledge, research outputs, prior frameworks | Yes |
| Target audience profile | M1 conception frameworks (customer definition) | Yes |
| Communication goal | User intent (educate, compare, persuade, explain) | Yes |
| Brand guidelines | M3 brand milestone outputs | No |

**Action:**

1. Define the primary communication goal:
   - Educate audience about complex topic?
   - Compare multiple options or features?
   - Present statistical findings?
   - Explain a process or workflow?
   - Show geographic distribution?
   - Demonstrate hierarchy or relationships?

2. Review the 10 infographic types and select the pattern that matches your goal:

| Type | Visual Pattern | Use Case | Key Elements |
|------|---------------|----------|--------------|
| **Information** | Icon + text blocks | Educational content, concepts | Large icons, brief text, color-coded sections |
| **List** | Numbered/icon grid | Tips, factors, steps | Icon grid, numbered items, visual markers |
| **Timeline** | Linear sequence | Historical events, milestones | Horizontal/vertical timeline, milestone markers |
| **Comparison** | Side-by-side split | Feature/product comparisons | Visual divider, contrasting colors, parallel sections |
| **Statistics** | Data visualization | Metrics, survey results | Large numbers, charts, graphs, percentages |
| **Flowchart** | Process flow | Decision trees, workflows | Boxes, arrows, decision points, connectors |
| **Hierarchy** | Pyramid/org chart | Organizational structures | Pyramid shape, top-down levels, connections |
| **Map** | Geographic visualization | Location data, distribution | Map background, markers, regional data |
| **Anatomical** | Labeled diagram | Parts breakdown, structure | Diagram with labels, callouts, annotations |
| **Mixed** | Multiple patterns | Complex topics | Combination of above types in sections |

3. Document content scope:
   - How many major sections will the infographic contain? (Minimum 2)
   - What key statistics or data points must be visible?
   - What concepts require visual explanation?

4. Verify infographic is the correct format:
   - Is this truly visual-first content? (If text-heavy, consider one-pager instead)
   - Does the content benefit from section-based vertical scrolling?
   - Will visual elements carry the primary message?

**Output:** Infographic type and content scope

| Output | Format | Purpose |
|--------|--------|---------|
| Infographic type selection | Document (type name + rationale) | Guides visual pattern selection |
| Content goal statement | One sentence | Clarifies communication objective |
| Section count and topics | List | Defines scope |

**Validation:**

How to know you're done correctly:

- [ ] Infographic type selected and documented with rationale
- [ ] Content goal statement is clear and specific
- [ ] Section topics identified (minimum 2 sections)
- [ ] Confirmed infographic format is appropriate (not text-heavy content)

---

## Task 2: Structure Content for Visual Communication

**Goal:** Organize raw content into scannable sections with visual-first information hierarchy.

**Inputs:** Content to be visualized

| Input | Source | Required |
|-------|--------|----------|
| Infographic type | Task 1 output | Yes |
| Raw content or data | User knowledge, research | Yes |
| Section topics | Task 1 output | Yes |

**Action:**

1. Create hero section content:
   - Write main title (5-10 words maximum)
   - Write subtitle or key statistic (one sentence)
   - Identify hero visual (icon, illustration, or key number)

2. For each content section:
   - Write section heading (2-5 words)
   - Identify 1-3 key visual elements (icons, charts, numbers)
   - Write minimal supporting text (brief descriptions only, no paragraphs)
   - Determine section background treatment (color, pattern, gradient)

3. Extract and highlight statistics:
   - Identify all numbers, percentages, metrics
   - For each statistic: write large display number + short label
   - Determine which statistics deserve 72px+ font size (hero statistics)

4. Convert text to visual elements:
   - Replace paragraphs with icon + brief text blocks
   - Convert lists to numbered items with visual markers
   - Transform processes into flowchart elements
   - Identify data that can become charts or graphs

5. Establish visual flow between sections:
   - Determine reading order (top to bottom)
   - Identify where visual connectors (arrows, lines) are needed
   - Plan transitions between sections

**Output:** Section outline with visual specifications

| Output | Format | Purpose |
|--------|--------|---------|
| Hero section specification | Document (title, subtitle, hero visual) | Defines above-the-fold content |
| Section outlines | Document per section (heading, visuals, text) | Guides design implementation |
| Statistics list | Table (number, label, prominence level) | Ensures data visibility |
| Visual flow diagram | Sketch or text description | Shows section connections |

**Validation:**

How to know you're done correctly:

- [ ] Hero section defined with title, subtitle, and hero visual
- [ ] Each section has heading, 1-3 visual elements, and minimal text
- [ ] All statistics extracted and prominence levels assigned
- [ ] Text converted to visual elements (no paragraphs remain)
- [ ] Visual flow between sections documented
- [ ] Content is scannable without deep reading

---

## Task 3: Select Visual Elements and Data Visualizations

**Goal:** Choose specific icons, charts, colors, and visual patterns that create cohesive visual communication.

**Inputs:** Visual specifications from content structure

| Input | Source | Required |
|-------|--------|----------|
| Section outlines | Task 2 output | Yes |
| Statistics list | Task 2 output | Yes |
| Brand guidelines | M3 brand milestone | No |
| Infographic type | Task 1 output | Yes |

**Action:**

1. Select icon style and sources:
   - Choose consistent icon style: line icons, filled icons, or illustrations
   - Identify icon library (Font Awesome, Feather Icons, Material Icons, custom)
   - Select specific icons for each visual element (use 64px-128px size range)
   - Verify icons are meaningful, not decorative

2. Define color scheme for sections:
   - Select 3-5 distinct background colors for sections
   - Choose accent color for key visuals and statistics
   - Verify all text has WCAG AA contrast on backgrounds (4.5:1 minimum)
   - Consider color-coding: each section type has unique color treatment

3. Choose data visualization methods:
   - For each statistic: determine display method (large number, bar chart, pie chart, line graph)
   - Select implementation approach: CSS-only, SVG, or JavaScript library (Chart.js)
   - Design large number displays: font size (72px-120px), accent color, label placement

4. Define background patterns and textures:
   - Select subtle patterns or gradients for sections
   - Ensure patterns don't reduce readability
   - Plan variation: different sections get different treatments

5. Specify visual connectors:
   - Choose arrow style for flow indicators
   - Define line thickness for connectors (2-4px recommended)
   - Select connector colors (typically accent color)

**Output:** Complete visual element specifications

| Output | Format | Purpose |
|--------|--------|---------|
| Icon selections | List with sources and sizes | Guides icon implementation |
| Color scheme | Palette with hex codes and usage rules | Ensures consistency |
| Data visualization specs | Table (statistic, method, implementation) | Guides chart creation |
| Background treatments | List per section (color, pattern, gradient) | Defines section aesthetics |
| Visual connector specs | Document (style, size, color) | Guides flow elements |

**Validation:**

How to know you're done correctly:

- [ ] Consistent icon style selected with specific icon choices documented
- [ ] Color scheme defined with 3-5 section colors and 1 accent color
- [ ] All text/background combinations meet WCAG AA contrast (4.5:1 minimum)
- [ ] Data visualization method chosen for each statistic
- [ ] Large statistics use 72px+ font size
- [ ] Background treatments specified for each section
- [ ] Visual connector style defined

---

## Task 4: Create Information Hierarchy

**Goal:** Establish clear visual priority ensuring most important information is most prominent.

**Inputs:** Visual elements and section structure

| Input | Source | Required |
|-------|--------|----------|
| Section outlines | Task 2 output | Yes |
| Visual element specs | Task 3 output | Yes |
| Statistics list | Task 2 output | Yes |

**Action:**

1. Define hero section hierarchy (above the fold):
   - Title: largest text element (48px-72px)
   - Key visual or statistic: most prominent visual element
   - Subtitle: secondary prominence (24px-32px)
   - Ensure all elements visible without scrolling (at 1920x1080)

2. Establish section header hierarchy:
   - Section headers: 36px-48px, bold weight
   - Use section-specific accent colors
   - Position prominently at top of each section

3. Set visual element prominence:
   - Primary icons: 96px-128px (focal point of section)
   - Secondary icons: 64px-96px (supporting elements)
   - Tertiary icons: 48px-64px (decorative or minor elements)

4. Define statistic hierarchy:
   - Hero statistics: 96px-120px font size (main findings)
   - Secondary statistics: 72px-96px (supporting data)
   - Tertiary statistics: 48px-72px (context numbers)
   - All statistics use accent color or high contrast

5. Set text hierarchy:
   - Supporting text: 18px-24px (brief descriptions)
   - Labels: 14px-18px (units, legends, annotations)
   - All text is secondary to visual elements

6. Create visual weight balance:
   - Most important information has largest size + highest contrast
   - Visual elements larger than text in all cases
   - Statistics and numbers more prominent than explanatory text

**Output:** Visual hierarchy specification

| Output | Format | Purpose |
|--------|--------|---------|
| Hierarchy diagram | Visual representation showing size/prominence relationships | Guides implementation |
| Typography scale | Table (element type, font size, weight, color) | Defines text sizing |
| Icon sizing rules | Table (icon role, size range) | Ensures icon prominence |
| Statistic prominence rules | Table (statistic type, size, color) | Highlights data |

**Validation:**

How to know you're done correctly:

- [ ] Hero section is most prominent (largest title, key visual above fold)
- [ ] Visual elements (icons, charts) are larger than text throughout
- [ ] Hero statistics use 96px+ font size
- [ ] Section headers clearly delineate sections (36px+ font)
- [ ] All text elements have clear hierarchy (no ambiguous sizing)
- [ ] Most important information has highest visual weight (size + contrast)

---

## Task 5: Design Layout and Flow

**Goal:** Build section-based vertical scroll layout with HTML/CSS implementing all visual specifications.

**Inputs:** All design specifications from prior tasks

| Input | Source | Required |
|-------|--------|----------|
| Section outlines | Task 2 output | Yes |
| Visual element specs | Task 3 output | Yes |
| Visual hierarchy | Task 4 output | Yes |
| Infographic type | Task 1 output | Yes |

**Action:**

1. Set up HTML structure:
   - Create semantic HTML5 with header, sections, footer
   - Each content section is a `<section>` element
   - Use proper heading hierarchy (h1 for title, h2 for section headers)
   - Include ARIA labels for accessibility

2. Implement hero section:
   - Full viewport height or prominent above-the-fold placement
   - Center-aligned title and subtitle
   - Hero visual (icon, illustration, or statistic) prominently placed
   - Ensure visible at 1920x1080 without scrolling

3. Build content sections with vertical flow:
   - Each section stacks vertically (full-width blocks)
   - Apply distinct background color/pattern per section
   - Generous padding between sections (80px-120px)
   - Content within sections centered or left-aligned based on type

4. Implement visual elements:
   - Place icons at specified sizes using CSS or SVG
   - Create data visualizations (charts, graphs) using chosen method
   - Display statistics with large font size, accent color, and clear labels
   - Add visual connectors (arrows, lines) between related elements

5. Apply typography scale:
   - Implement font sizes per hierarchy specification
   - Use high-contrast colors for all text
   - Verify WCAG AA compliance (4.5:1 contrast ratio minimum)

6. Add background treatments:
   - Apply colors, gradients, or subtle patterns per section
   - Ensure backgrounds don't reduce content readability
   - Create visual distinction between sections

7. Optimize for vertical scrolling:
   - Design for 1920x1080 target resolution (landscape) or 1080x1920 (portrait)
   - Sections should be self-contained and scannable
   - Smooth visual transitions between sections
   - No horizontal scrolling required

8. Add optional footer:
   - Subtle, non-distracting design
   - Attribution, branding, or source citations if needed

**Output:** Complete HTML/CSS infographic implementation

| Output | Format | Purpose |
|--------|--------|---------|
| HTML file | Semantic HTML5 document | Infographic structure |
| CSS file | Stylesheet with all visual specifications | Visual styling |
| Asset files | Icons, images, charts as separate files or inline SVG | Visual elements |

**Validation:**

How to know you're done correctly:

- [ ] HTML uses semantic structure (header, sections, footer)
- [ ] Hero section visible without scrolling at 1920x1080
- [ ] All sections stack vertically with distinct backgrounds
- [ ] Visual elements implemented at specified sizes (icons 64px+, hero stats 96px+)
- [ ] Typography follows hierarchy specification
- [ ] All text meets WCAG AA contrast requirements (4.5:1 minimum)
- [ ] Background treatments applied per section
- [ ] Infographic scrolls vertically without horizontal scroll
- [ ] Visual connectors (arrows, lines) implemented where specified

---

## Task 6: Validate Visual Clarity

**Goal:** Verify infographic meets design criteria and doesn't fall into common anti-patterns.

**Inputs:** Completed infographic

| Input | Source | Required |
|-------|--------|----------|
| HTML/CSS implementation | Task 5 output | Yes |
| Visual hierarchy specification | Task 4 output | Yes |
| Infographic type selection | Task 1 output | Yes |

**Action:**

1. Verify visual-first design:
   - Open infographic in browser at 1920x1080 resolution
   - Check that icons, charts, and illustrations are primary content
   - Confirm text is secondary (brief descriptions only)
   - No paragraphs or text-heavy sections present

2. Validate section-based layout:
   - Each major section has distinct background color or pattern
   - Sections are self-contained and scannable independently
   - Vertical flow is clear (top to bottom)
   - No layout that attempts to fit everything in single viewport

3. Check statistic prominence:
   - Measure font size of all statistics (hero: 96px+, secondary: 72px+)
   - Statistics use accent color or high contrast
   - Numbers are immediately visible when scanning
   - No statistics buried in text blocks

4. Verify icon prominence:
   - Measure primary icon sizes (should be 64px+ minimum)
   - Icons are meaningful and support content understanding
   - Icon style is consistent throughout
   - Icons are not small or decorative-only

5. Validate color and contrast:
   - Test all text/background combinations with contrast checker
   - All combinations must meet WCAG AA (4.5:1 minimum)
   - Color-coding creates visual distinction between sections
   - Backgrounds not flat or uniform (patterns, gradients present)

6. Check data visualization:
   - Charts and graphs present for statistical content
   - Data visualizations are large and readable
   - No data presented only in text form without visualization

7. Verify visual flow:
   - Visual connectors (arrows, lines) guide eye through content
   - Logical reading order from top to bottom
   - Sections connect coherently

8. Anti-pattern check:
   - NOT text-heavy (would be one-pager, not infographic)
   - NOT single viewport design (should scroll vertically)
   - NOT small icons (64px+ required)
   - NOT hidden statistics (numbers should be large and prominent)
   - NOT flat backgrounds (visual interest required)
   - NOT inconsistent icon styles (single style throughout)
   - NOT low contrast (WCAG AA required)

9. Test at target resolution:
   - View at 1920x1080 (landscape) or 1080x1920 (portrait)
   - Hero section visible without scrolling
   - All elements render correctly without overflow or distortion

**Output:** Validation results and revision list

| Output | Format | Purpose |
|--------|--------|---------|
| Validation checklist | Completed checklist (all items passed) | Confirms quality |
| Revision list | Document listing issues found | Guides corrections |
| Anti-pattern assessment | Document noting any anti-patterns present | Prevents common mistakes |

**Validation:**

How to know you're done correctly:

- [ ] Visual-first design confirmed (visuals primary, text secondary)
- [ ] Section-based layout verified (distinct backgrounds, vertical flow)
- [ ] Statistics prominence checked (96px+ hero, 72px+ secondary)
- [ ] Icon sizes validated (64px+ primary icons)
- [ ] All text/background combinations meet WCAG AA (4.5:1)
- [ ] Data visualizations present for all statistical content
- [ ] Visual flow verified (connectors guide reading)
- [ ] No anti-patterns detected (text-heavy, small icons, hidden stats, flat backgrounds, inconsistent icons, low contrast)
- [ ] Renders correctly at target resolution (1920x1080 or 1080x1920)
- [ ] Revision list created for any issues found

---

## Pitfalls

**Pitfall: Creating Text-Heavy Layouts That Resemble One-Pagers**

Infographics prioritize visual elements as the primary communication method, with text playing a supporting role. Attempting to explain concepts through paragraphs or extensive text blocks defeats the purpose of the format. This mistake often occurs when converting existing documents to infographic format without restructuring content.

**Instead:** Convert text to visual elements. Replace paragraphs with icon + brief label. Extract statistics and display them as large numbers. Use charts and graphs instead of describing data in sentences. If content requires extensive text explanation, use a one-pager format instead.

---

**Pitfall: Using Small or Decorative-Only Icons**

Icons below 48px appear decorative rather than functional, failing to communicate information visually. Small icons force viewers to rely on text instead of visual scanning, undermining the infographic's core purpose. This often happens when designers treat infographics like text documents with icon embellishments.

**Instead:** Use 64px-128px icons as primary content carriers. Each icon should be meaningful and support content understanding. Viewers should grasp key concepts by scanning icons alone, even before reading text labels.

---

**Pitfall: Burying Statistics in Text or Using Small Font Sizes**

Numbers and data are the most memorable elements of an infographic, but only if they're immediately visible. Embedding statistics within sentences or displaying them at body text size (18px-24px) hides the data and reduces impact. Sophisticated practitioners sometimes underestimate the importance of visual prominence for numerical data.

**Instead:** Extract all statistics and display them at 72px+ font size (96px-120px for hero statistics). Use accent colors for numbers. Add brief labels but keep the number itself dominant. Statistics should be visible when scanning the page from a distance.

---

**Pitfall: Attempting Single-Viewport Design**

Unlike presentations or one-pagers, infographics are designed for vertical scrolling through distinct sections. Trying to compress all content into a single viewport (to avoid scrolling) creates cluttered, cramped layouts that sacrifice readability and visual impact.

**Instead:** Embrace vertical scroll. Design sections to stack with generous spacing (80px-120px between sections). Each section should be self-contained and scannable. Users expect to scroll through infographics—the format is optimized for it.

---

**Pitfall: Using Flat, Uniform Backgrounds Throughout**

Monochromatic or single-color backgrounds create visual monotony, making it difficult to distinguish between sections and reducing engagement. This often results from applying minimalist design principles too rigidly without considering the infographic's need for visual interest.

**Instead:** Use distinct background treatments for each section: different colors, subtle patterns, or gradients. Color-code sections by topic or type. Visual variety helps guide the eye, improves scannability, and makes the infographic more memorable.

---

**Pitfall: Mixing Icon Styles**

Using line icons in one section, filled icons in another, and photorealistic illustrations in a third creates visual inconsistency that appears unprofessional. This typically happens when sourcing icons from multiple libraries without establishing style guidelines first.

**Instead:** Select one icon style (line, filled, or illustration) before beginning design and source all icons from compatible libraries. Consistency in visual language is critical for professional presentation and cognitive coherence.

---

**Pitfall: Presenting Data Without Visualization**

Listing numbers or statistics in text form without accompanying charts, graphs, or visual representations misses the core purpose of infographics. Data visualization makes patterns immediately apparent and increases memorability far beyond text-only presentation.

**Instead:** For every dataset, choose an appropriate visualization: bar charts for comparisons, line graphs for trends, pie charts for proportions. Use CSS, SVG, or libraries like Chart.js to implement. Large standalone numbers work for single statistics; groups of data require visual representation.

---

## Integration

**Prerequisites:** Can execute independently or use prior M4 frameworks

**Builds on:**

| Framework | Output Used |
|-----------|-------------|
| Value Proposition Canvas (M1) | Core value propositions and customer insights |
| Brand Identity (M3) | Brand colors, typography, visual style |
| One-Pager (M4) | Core messaging and content structure |

**Feeds into:**

| Framework | Output Provided |
|-----------|-----------------|
| Landing Page (M4) | Visual elements, statistics, brand-consistent design |
| Presentation (M4) | Data visualizations, statistics displays |
| MVP Documentation (M6) | Visual explanations of product features |

---

## Success Criteria

This framework is complete when:

- [ ] Infographic type selected and appropriate for content goals
- [ ] Content structured with visual-first hierarchy (visuals primary, text secondary)
- [ ] Visual elements specified: icons (64px+), colors (WCAG AA contrast), data visualizations
- [ ] Information hierarchy established with hero section prominent above fold
- [ ] HTML/CSS implementation complete with section-based vertical layout
- [ ] Validation passed: visual-first design, prominent statistics (72px+), color-coded sections, consistent icons
- [ ] No anti-patterns present: not text-heavy, not single-viewport, not small icons, not low contrast
- [ ] Renders correctly at target resolution (1920x1080 landscape or 1080x1920 portrait)
- [ ] All task validation criteria have been met
- [ ] Outputs documented and accessible

---

## For AI Agents

**Execution:**

1. MUST read this framework completely before starting
2. MUST track progress: "Currently in Task [N]: [Task Name]"
3. MUST confirm each task's validation criteria before proceeding
4. MUST update founder log with key design decisions

**Tasks:**
- Each task MUST be completed fully before moving to next
- Task outputs become inputs to subsequent tasks

**Validation points:**
- After Task 1: MUST confirm infographic is appropriate format (not text-heavy)
- After Task 3: MUST verify all color contrasts meet WCAG AA
- After Task 5: MUST check hero section visibility at 1920x1080
- After Task 6: MUST ensure zero anti-patterns; if any detected, return to appropriate task

---