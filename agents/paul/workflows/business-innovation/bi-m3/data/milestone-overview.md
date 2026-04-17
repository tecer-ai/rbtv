# M3 Brand Milestone Overview

**Purpose:** Reference document for the M3 Brand milestone workflow. Defines framework dependencies, recommended execution order, success criteria, and referral logic.

---

## Framework Sequence and Dependencies

### Recommended Execution Order

The recommended order follows brand_process.md Steps 2-7 plus brandbook synthesis, optimizing for learning flow and dependency management:

1. **Brand Archetypes** → 2. **Brand Prism** → 3. **Golden Circle** → 4. **Brand Positioning** → 5. **Messaging Architecture** → 6. **Tone of Voice** → 7. **Brandbook**

**Rationale:**
- Brand Archetypes establishes foundational personality (informs all other frameworks)
- Brand Prism builds on archetype to define six facets of identity
- Golden Circle articulates purpose (Why/How/What) grounded in prism
- Brand Positioning uses archetype, prism, and golden circle to craft competitive statement
- Messaging Architecture translates positioning into hierarchical messages
- Tone of Voice operationalizes archetype and personality into writing guidelines
- Brandbook synthesizes all 6 frameworks into a single reference document with visual identity (logo, colors, typography, imagery, iconography)

---

## Framework Details

### [BA] Brand Archetypes

**Recommended Order:** 1st  
**Prerequisites:** M1 (Working Backwards, JTBD, Lean Canvas), M2 (3+ frameworks completed)  
**Output:** `brand-archetypes.md`  
**Workflow:** `../bi-m3-brand-archetypes/workflow.md`

**Purpose:** Identify the universal archetype (from 12 Jungian archetypes) that best represents the brand's personality and customer relationship.

**Key Deliverables:**
- Primary archetype selection with evidence-based justification
- Optional secondary archetype for nuance
- Expression across voice, visuals, relationship, content themes
- Differentiation analysis against competitor archetypes

**Feeds Forward To:**
- Brand Prism (personality facet)
- Golden Circle (core motivation alignment)
- Tone of Voice (voice character)
- Messaging Architecture (content themes)
- M4 Design Brief (visual direction)

---

### [BP] Brand Prism

**Recommended Order:** 2nd  
**Prerequisites:** Brand Archetypes (recommended), M1 (Working Backwards, JTBD, Lean Canvas), M2 (3+ frameworks)  
**Output:** `brand-prism.md`  
**Workflow:** `../bi-m3-brand-prism/workflow.md`

**Purpose:** Map brand identity using Kapferer's six-facet prism model (physique, personality, culture, relationship, reflection, self-image).

**Key Deliverables:**
- All six facets defined with consistency checks
- External facets (physique, personality, relationship)
- Internal facets (culture, reflection, self-image)
- Cross-facet coherence validation

**Feeds Forward To:**
- Golden Circle (culture and beliefs)
- Brand Positioning (reflection and self-image)
- Tone of Voice (personality traits)
- Messaging Architecture (relationship dynamics)
- M4 Design Brief (physique and visual identity)

---

### [GC] Golden Circle

**Recommended Order:** 3rd  
**Prerequisites:** Brand Prism (recommended), Brand Archetypes (recommended), M1 (Working Backwards, Lean Canvas), M2 (3+ frameworks)  
**Output:** `golden-circle.md`  
**Workflow:** `../bi-m3-golden-circle/workflow.md`

**Purpose:** Define the brand's purpose using Sinek's Why/How/What framework.

**Key Deliverables:**
- Why: The purpose, cause, or belief (not "to make money")
- How: The specific approach or values that differentiate execution
- What: The tangible products or services offered
- Authenticity validation (connects to customer's emotional job from JTBD)

**Feeds Forward To:**
- Brand Positioning (purpose-driven differentiation)
- Messaging Architecture (brand promise foundation)
- Tone of Voice (purpose-aligned language)
- M4 Design Brief (purpose-driven visual narrative)

---

### [PO] Brand Positioning

**Recommended Order:** 4th  
**Prerequisites:** Golden Circle (recommended), Brand Prism (recommended), Brand Archetypes (recommended), M1 (Working Backwards, JTBD, Lean Canvas), M2 (TAM/SAM/SOM for competitive context)  
**Output:** `brand-positioning.md`  
**Workflow:** `../bi-m3-brand-positioning/workflow.md`

**Purpose:** Craft a single-sentence positioning statement that defines the brand's unique market position.

**Key Deliverables:**
- Positioning statement: "For [target] who [need], [brand] is the [category] that [benefit], unlike [alternative] which [limitation]."
- Perceptual map showing competitive position on 2 key dimensions
- Differentiation validation (unique, defensible, relevant, credible)
- Alignment with Brand Prism, Golden Circle, and Lean Canvas UVP

**Feeds Forward To:**
- Messaging Architecture (positioning as foundation for key messages)
- Tone of Voice (positioning-aligned language)
- M4 Design Brief (positioning-driven visual differentiation)
- M5 Market Validation (positioning testing)

---

### [MA] Messaging Architecture

**Recommended Order:** 5th  
**Prerequisites:** Brand Positioning (recommended), Golden Circle (recommended), Brand Prism (recommended), M1 (Working Backwards, JTBD, Lean Canvas), M2 (3+ frameworks)  
**Output:** `messaging-architecture.md`  
**Workflow:** `../bi-m3-messaging-architecture/workflow.md`

**Purpose:** Build hierarchical messaging structure from brand promise to audience-specific messages to proof points to CTAs.

**Key Deliverables:**
- 4-level hierarchy: Brand Promise → Key Messages → Proof Points → CTAs
- Audience-specific message variants (early adopters, mainstream, partners, investors)
- Journey stage mapping (awareness, consideration, decision, retention)
- Traceability to validated assumptions and framework outputs

**Feeds Forward To:**
- Tone of Voice (message examples for tone application)
- M4 Prototypation (copy for prototype)
- M5 Market Validation (message testing)
- M6 MVP (product copy and marketing materials)

---

### [TV] Tone of Voice

**Recommended Order:** 6th  
**Prerequisites:** Messaging Architecture (recommended), Brand Archetypes (recommended), Brand Prism (recommended), M1 (Working Backwards, JTBD), M2 (3+ frameworks)  
**Output:** `tone-of-voice.md`  
**Workflow:** `../bi-m3-tone-of-voice/workflow.md`

**Purpose:** Define verbal identity through tone dimensions, do/don't examples, and context-specific adjustments.

**Key Deliverables:**
- 3-5 tone dimensions with slider positions (e.g., formal↔casual, serious↔playful)
- Do/don't examples for each dimension
- Context-specific tone adjustments (marketing, support, error messages, onboarding)
- Sample copy for 3-5 common scenarios
- Consistency with archetype and brand personality

**Feeds Forward To:**
- Brandbook (voice and tone guidelines for brandbook compilation)
- M4 Prototypation (copy writing guidelines)
- M5 Market Validation (customer communication tone)
- M6 MVP (product copy, UI microcopy, support materials)

---

### [BB] Brandbook

**Recommended Order:** 7th (final)  
**Prerequisites:** ALL 6 preceding frameworks (mandatory, no override)  
**Output:** `brandbook.md` + `brandbook-assets/` (logo files, imagery references)  
**Workflow:** `../bi-m3-brandbook/workflow.md`

**Purpose:** Synthesize all M3 framework outputs into a single, comprehensive brandbook document with visual identity specifications created through AI-assisted image generation.

**Key Deliverables:**
- Brand Identity section (mission, vision, persona, audience, values, brand story) compiled from frameworks
- Visual Guidelines (logo variations, color palette with HEX/RGB/CMYK, typography hierarchy, imagery style, iconography)
- Logo and imagery assets generated via AI image prompts (founder iterates and approves)
- Messaging & Tone section (voice, tone guidelines, tagline, value proposition, key messaging)
- One-page Quick Reference Sheet
- All visual elements with explicit do's/don'ts

**Feeds Forward To:**
- M4 Prototypation (canonical visual and verbal reference for all design and copy)
- M5 Market Validation (brand-consistent test materials)
- M6 MVP (production brand standard for all assets)

---

## Success Criteria

M3 Brand milestone is complete when:

1. ✅ Brand Archetypes analysis exists with primary archetype selected and justified
2. ✅ Brand Prism document exists with all six facets defined and consistent
3. ✅ Golden Circle document exists with authentic Why, How, What
4. ✅ Positioning statement exists as a single sentence with competitive differentiation
5. ✅ Tone of Voice guide exists with dimensions, do/don't examples, and sample copy
6. ✅ Messaging Architecture exists with hierarchical structure and audience variants
7. ✅ Brandbook exists with visual identity, compiled brand sections, and quick reference sheet
8. ✅ Project-memo Progress > Brand section lists all completed frameworks
9. ✅ Founder can articulate: Who is our brand? What do we stand for? How do we sound? How are we different? What do we look like?

---

## Referral Logic

### Milestone → Framework
- M3 milestone workflow (`bi-m3/workflow.md`) presents framework menu via `steps-c/step-01-init.md`
- User selects a framework [BA/BP/GC/PO/MA/TV/BB]
- Step-01 updates project-memo frontmatter `currentFramework`
- Step-01 loads selected framework workflow

### Framework → Milestone
- Framework workflow synthesis step (last step) updates project-memo.md:
  - Adds framework ID to `stepsCompleted` array
  - Writes synthesis to Progress > Brand subsection
- Synthesis step presents menu: [B] Back to M3 or [E] Exit
- [B] loads `../../workflow.md` which routes to `steps-c/step-01-init.md`
- Step-01 reads updated stepsCompleted and presents framework menu with updated status

### State Tracking
- **project-memo.md frontmatter:**
  - `currentMilestone: m3-brand`
  - `currentFramework: bi-m3-[framework-name]`
  - `stepsCompleted: [array of completed framework IDs]`
- **Framework IDs:**
  - `bi-m3-brand-archetypes`
  - `bi-m3-brand-prism`
  - `bi-m3-golden-circle`
  - `bi-m3-brand-positioning`
  - `bi-m3-messaging-architecture`
  - `bi-m3-tone-of-voice`
  - `bi-m3-brandbook`

---

## Notes

- While the recommended order optimizes learning flow, founders can select any framework with met prerequisites
- Prerequisite checking is advisory, not enforced (override allowed with warning) — exception: Brandbook requires all 6 frameworks, no override
- Each framework synthesis step suggests the next recommended framework based on this order
- All frameworks update project-memo.md before returning to milestone menu
