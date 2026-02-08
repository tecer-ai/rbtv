---
---

# Prototypation Process

**Purpose:** Detailed process guide for Milestone 4 (Prototypation) of the founder module. Transforms validated concepts and brand identity into working HTML prototypes suitable for friends & family testing.

**Goal:** Build a working HTML prototype that communicates the product vision, tests user comprehension, and enables early feedback from a trusted circle before market-facing validation in M5.

---

## Inputs

| Input | Source |
|-------|--------|
| Validated business concept | M1 Conception frameworks |
| Technical and financial feasibility assessment | M2 Validation frameworks |
| Brand identity and visual direction | M3 Brand frameworks |
| Target customer profile | M1 Working Backwards, JTBD |
| Value proposition | M1 Lean Canvas, Problem-Solution Fit |

---

## Outputs

| Output | Format |
|--------|--------|
| User flow map | Markdown document (`[project]/docs/founder/prototypation/user_flow_map.md`) |
| Information architecture | Markdown document (`[project]/docs/founder/prototypation/information_architecture.md`) |
| Design brief | Markdown document (`[project]/docs/founder/prototypation/design_brief.md`) |
| Design specifications | JSON file (`[project]/docs/founder/prototypation/design-[artifact_type].json`) |
| HTML prototype | HTML/CSS files (`[project]/deliverables/[material]/`) |
| Heuristic evaluation report | Markdown document (`[project]/docs/founder/prototypation/heuristic_evaluation.md`) |
| M4 Founder Diary | Markdown table (`[project]/docs/founder/prototypation/m4_founder_diary.md`) |

---

## Steps Summary

| Step | Action | Framework | Output |
|------|--------|-----------|--------|
| 1 | Initialize M4 structure and review prior milestones | — | M4 folder structure, context review |
| 2 | Map user flows and conversion paths | User Flow Mapping | User flow map document |
| 3 | Define information architecture and content hierarchy | Information Architecture | IA document |
| 4 | Establish design direction and visual system | Design Brief + Design Tokens | design_brief.md + design.json |
| 5 | Build HTML prototype sections | Atomic Design, Conversion-Centered Design, Progressive Disclosure | Working HTML prototype |
| 6 | Ensure accessibility and responsive behavior | WCAG Accessibility, Responsive Design | Accessible, responsive prototype |
| 7 | Evaluate usability and fix issues | Heuristic Evaluation | Evaluation report, revised prototype |
| 8 | Prepare for friends & family testing | — | Test protocol, updated diary |

---

## Step 1: Initialize M4 Structure

**Inputs:** Project name, prior milestone outputs

**Action:**
1. Create milestone folder: `[project]/docs/founder/prototypation/`
2. Initialize founder diary from the template: [founder_diary.md](../templates/founder_diary.md)
3. Review M1 project memo for business concept, value proposition, and target customer
4. Review M3 brand outputs for visual direction (if M3 complete)
5. Determine artifact types needed: landing_page, website, presentation, one_pager, infographic
6. Update Session Status in m4_founder_diary.md

**Output:** M4 folder structure with diary initialized, clear understanding of what to prototype

**Framework Reference:** None (structural setup)

---

## Step 2: Map User Flows

**Inputs:** Value proposition, target customer profile, conversion goals

**Action:**
1. Define primary user flow: the path from first contact to conversion
2. Identify entry points: how users arrive (ad click, organic search, direct link, referral)
3. Map each screen or section the user encounters in sequence
4. Define decision points where users choose between actions
5. Identify the single conversion goal per artifact (signup, download, purchase, inquiry)
6. Document exit points and potential drop-off risks
7. Save to `[project]/docs/founder/prototypation/user_flow_map.md`

**Output:** User flow map with entry points, screens, decisions, and conversion goal

**Framework Reference:** User Flow Mapping

---

## Step 3: Define Information Architecture

**Inputs:** User flow map, content from M1/M3 frameworks

**Action:**
1. List all content elements the prototype must communicate (value proposition, benefits, social proof, CTAs)
2. Organize content into sections following conversion funnel logic: attention → interest → credibility → action
3. Define content hierarchy within each section (what is primary, secondary, supporting)
4. Map content sections to user flow screens
5. Determine content density per section (how much information per viewport)
6. Save to `[project]/docs/founder/prototypation/information_architecture.md`

**Output:** Information architecture document with section structure and content hierarchy

**Framework Reference:** Information Architecture

---

## Step 4: Establish Design Direction

**Inputs:** Brand identity (M3), information architecture, user flow map

**Action:**
1. Invoke lavoisier agent for creative discovery: [lavoisier.md](../agents/lavoisier.md)
2. Lavoisier guides through Acts 1-4: initial discovery → inspiration research → iterative refinement → design outputs
3. Lavoisier creates design_brief.md (narrative visual direction) and design-[artifact_type].json (layout specifications)
4. Review design outputs against M3 brand identity for consistency
5. Files saved to `[project]/docs/founder/prototypation/` or `[project]/deliverables/[material]/`

**Output:** design_brief.md and design-[artifact_type].json

**Framework Reference:** Read [design_brief.md](design_brief.md) (template), [design.json](design.json) (schema)

---

## Step 5: Build HTML Prototype

**Inputs:** Design brief, design JSON, information architecture, user flow map

**Action:**
1. Build component inventory following Atomic Design principles: atoms (buttons, inputs, labels) → molecules (form groups, card elements) → organisms (hero sections, testimonial blocks) → templates (page layouts)
2. Implement sections following design-[artifact_type].json layout specifications
3. Apply Conversion-Centered Design principles: single conversion goal, clear visual hierarchy, directional cues toward CTA, high-contrast CTA buttons, minimal distractions
4. Apply Progressive Disclosure: show essential information first, reveal details on interaction, avoid overwhelming users with all information at once
5. For artifact-specific guidance, read framework docs:
   - Landing pages: [landing_page.md](prototypation_frameworks/landing_page.md)
   - Infographics: [infographic.md](prototypation_frameworks/infographic.md)
6. Save HTML/CSS to `[project]/deliverables/[material]/`

**Output:** Working HTML prototype with all sections implemented

**Framework Reference:** Atomic Design, Conversion-Centered Design, Progressive Disclosure

---

## Step 6: Ensure Accessibility and Responsiveness

**Inputs:** HTML prototype

**Action:**
1. Test responsive behavior at breakpoints: 375px (mobile), 768px (tablet), 1200px+ (desktop)
2. Verify CTA visible above fold at all breakpoints
3. Check touch targets meet 44px minimum height on mobile
4. Validate WCAG AA compliance:
   - Color contrast ratios ≥ 4.5:1 for text
   - All images have alt text
   - Heading hierarchy is logical (h1 → h2 → h3)
   - Keyboard navigation works (tab order, focus states)
   - Form inputs have labels
5. Fix all violations before proceeding
6. Test on actual mobile device (not just browser resize)

**Output:** Accessible, responsive prototype passing WCAG AA

**Framework Reference:** WCAG Accessibility, Responsive Design

---

## Step 7: Evaluate Usability

**Inputs:** Completed prototype

**Action:**
1. Conduct heuristic evaluation against Nielsen's 10 usability heuristics:
   - Visibility of system status
   - Match between system and real world
   - User control and freedom
   - Consistency and standards
   - Error prevention
   - Recognition rather than recall
   - Flexibility and efficiency of use
   - Aesthetic and minimalist design
   - Help users recognize and recover from errors
   - Help and documentation
2. Check for conversion anti-patterns: buried CTA, navigation menus on landing pages, generic copy, multiple competing goals, poor mobile experience, slow load times
3. Document findings with severity ratings (Critical, Major, Minor, Cosmetic)
4. Fix Critical and Major issues before F&F testing
5. Save evaluation to `[project]/docs/founder/prototypation/heuristic_evaluation.md`

**Output:** Heuristic evaluation report with issues categorized by severity

**Framework Reference:** Heuristic Evaluation

---

## Step 8: Prepare for Friends & Family Testing

**Inputs:** Revised prototype, evaluation report

**Action:**
1. Define test objectives: what questions must F&F testing answer?
   - Do people understand the value proposition within 5 seconds?
   - Can they identify what the product does and who it is for?
   - Do they know what action to take (CTA clarity)?
   - What questions or concerns do they raise?
2. Prepare test protocol:
   - Show prototype for 5 seconds, then ask: "What is this product/service?"
   - Let tester explore freely, observe where they click and hesitate
   - Ask: "What would you do next?" at each screen
   - Ask: "What is confusing or unclear?"
   - Ask: "Would you use this? Why or why not?"
3. Identify 5-10 testers from friends & family (varied backgrounds)
4. Update project memo Prototypation section with completed frameworks
5. Update m4_founder_diary.md with key design decisions and test preparation
6. Log significant decisions to diary

**Output:** Test protocol, updated project memo and diary

**Framework Reference:** None (synthesis and preparation)

---

## Success Criteria

Prototypation milestone is complete when:

- [ ] User flow map exists with entry points, screens, decisions, and conversion goal
- [ ] Information architecture defines content hierarchy and section structure
- [ ] Design brief and design JSON exist with visual direction and layout specs
- [ ] HTML prototype is functional with all sections implemented
- [ ] Prototype passes WCAG AA accessibility (contrast, keyboard nav, alt text, headings)
- [ ] Prototype is responsive at 375px, 768px, and 1200px+
- [ ] Heuristic evaluation completed with Critical/Major issues resolved
- [ ] F&F test protocol prepared with clear objectives and 5-10 testers identified
- [ ] Project memo Progress > Prototypation section updated
- [ ] M4 founder diary has at least 2 entries documenting key design decisions

---

## Next Milestone

Once Prototypation is complete, proceed to M5: Market Validation (market_validation_process.md) to test the prototype with real potential customers and validate demand, pricing, and channels.

---

