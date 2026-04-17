# Pitch Workflow Merge Audit

## workflow.md Differences

| Field | Investor | Client | Merge Strategy |
|-------|----------|--------|----------------|
| name | `investor-pitch-creation` | `client-pitch-creation` | `pitch-creation` (shared) |
| description | "Build investor pitch decks through narrative-first stress-testing, data validation, and research prompting" | "Build client/sales pitch decks through narrative-first buyer stress-testing, ROI validation, and research prompting" | Conditional description based on `{pitch_type}` |
| outputFolder | `{bmad_output}/{project-name}/_fundraising/pitch-deck` | `{bmad_output}/{project-name}/_clients/pitch-deck` | Conditional: `_fundraising` vs `_clients` based on `{pitch_type}` |
| Goal statement | "Build investor pitch decks that survive due diligence" | "Build client/sales pitch decks that survive procurement committees" | Conditional |
| Your Role | "The Investor ... write a check" | "The Buyer ... sign a contract" | Conditional |
| Core Principle #2 | "Stress-Test Everything" (investor perspective) | "Buyer Stress-Test" (buyer perspective) | Conditional label only |
| Mode table output | "investor pitch" | "client pitch" | Conditional |
| Mode note | "Investor agent" | "The Buyer agent" | Conditional |
| Step 01 purpose | "confirm investor pitch context" | "confirm client pitch context" | Conditional |
| Step 03 purpose | "inline investor stress-testing" | "inline buyer stress-testing" | Conditional |
| Step 04 purpose | "what data would validate each slide" | "ROI, proof points, case study needs" | Conditional |
| Step 05 purpose | "counter-thesis prompt" | "objection research" | Conditional |
| Knowledge file note | "Pitch deck best practices (YC, Sequoia, a16z, Kawasaki)" | "Pitch deck best practices (client section)" | Conditional |

**Structural differences:** None. Both have identical field names, same step counts, same file references, same architecture.

---

## Step-by-Step Comparison

### Step 01: Init

- **Status:** Structural differences
- **Differences:**
  1. **Title:** "Initialize Investor Pitch" vs "Initialize Client Pitch"
  2. **Step goal:** "confirm investor pitch scope" vs "understand the target client/audience"
  3. **Role reinforcement:** "The Investor ... VC partner ... writing a check" vs "The Buyer ... procurement VP ... signing a contract"
  4. **Step-specific rule:** "exclusively for investor pitches (fundraising: VCs, angels, accelerators)" vs "exclusively for client/sales pitches (winning customers or partnerships)" + extra rule "Understanding the TARGET CLIENT is critical"
  5. **Output folder path:** `_fundraising/pitch-deck` vs `_clients/pitch-deck`
  6. **Confirmation message:** Different wording (investor vs buyer framing)
  7. **Client has extra section 2:** "Understand the Target Client" (5 questions about who the pitch is for, their role, deal size, current solution, trigger) — sets `{target_client}` and `{deal_context}`. Investor version has no equivalent.
  8. **Section numbering shifts:** Investor has 5 sections, client has 6 (due to inserted target client section)
  9. **Confirm Setup summary:** Investor shows "Investor Pitch Setup" with 4 deliverables; Client shows "Client Pitch Setup" with target/deal context and 4 deliverables (slightly different wording)
  10. **Success metrics:** Investor: "Mode detected, Output path confirmed"; Client adds "Target client and deal context understood"
  11. **Failure metrics:** Investor: "Wrong output path"; Client: "Not understanding who the pitch is FOR"
- **Merge strategy:** Use `{pitch_type}` conditionals. Client-only "Understand the Target Client" section wrapped in `If pitch_type = client` block. All role references parameterized. Output path uses conditional subfolder.

### Step 02: Context Gather

- **Status:** Structural differences
- **Differences:**
  1. **Step goal:** Investor focuses on "pitch-relevant content"; Client adds "what a CLIENT buyer cares about: their problem, your solution, proof it works, and why you vs. alternatives"
  2. **Role reinforcement:** "The Investor mining founder documents for the strongest possible pitch material" vs "The Buyer mining founder documents for the content that would convince a procurement committee"
  3. **Step-specific rule:** "Use investor-focused search queries" vs "Use CLIENT-FOCUSED search queries (not investor-focused)"
  4. **Context-distill conversation context strings:** "Building an investor pitch deck for {project_name}" vs "Building a client pitch deck for {project_name} targeting {target_client}"
  5. **M1 specific request:** Investor extracts "(1) core problem, (2) key differentiators (max 3), (3) target customer, (4) competitive positioning, (5) primary value proposition, (6) contrarian market insights" vs Client extracts "(1) specific problem the TARGET CLIENT experiences, (2) solution benefits from client's perspective (max 5), (3) how the solution works, (4) competitive alternatives, (5) primary value proposition from buyer's POV, (6) jobs-to-be-done"
  6. **M2 specific request:** Investor: "TAM, SAM, SOM; unit economics" vs Client: "pricing structure/tiers; ROI metrics; implementation timeline; pilot results; technology readiness"
  7. **M3 specific request:** Investor: "brand archetype, color palette, typography, tagline, tone" vs Client: "brand positioning vs competitors, B2B messaging, trust signals, tone, tagline"
  8. **Context folder request:** Investor: "market research, competitors, industry trends, customer quotes, traction" vs Client: "customer feedback/testimonials, case study material, competitors from buyer's view, industry benchmarks, proof points"
  9. **Compiled brief structure:** Investor: Problem/Solution/Market Size/Traction/Unit Economics/Competitive Position/Brand/Why Now/Team/Gaps vs Client: Their Problem/Current Solution/Your Solution/How It Works/Proof Points/Competitive Alternatives/Pricing & ROI/Brand/Gaps
  10. **Presentation message:** Investor: "what I extracted from your founder documents" vs Client: "what I extracted from your founder documents, viewed through a buyer's lens"
  11. **Success metrics:** Investor: "organized by deck section" vs Client: "CLIENT-focused framing (their problem, not your features)"
  12. **Failure metrics:** Client adds "Framing content from vendor's perspective instead of buyer's"
- **Merge strategy:** Extensive `{pitch_type}` conditionals throughout. Context-distill queries, brief structure, and presentation framing all switch based on type. This is the most divergent step file.

### Step 03: Narrative

- **Status:** Structural differences
- **Differences:**
  1. **Title:** "Narrative Draft with Investor Stress-Testing" vs "Narrative Draft with Buyer Stress-Testing"
  2. **Step goal:** "defend in a partner meeting" vs "survive a procurement committee review"
  3. **Role reinforcement:** "The Investor ... write a check ... Monday partners meeting" vs "The Buyer ... sign a contract ... shortlist"
  4. **Extra client rule:** "Frame EVERYTHING from the client's perspective, never from the vendor's"
  5. **Slide count guidance:** "12-15 slides" vs "10-12 slides"
  6. **Slide arc:** Investor has 13-point arc (Title, Problem-data, Problem-human, Solution, Why Now, Traction, Market Size, Competition, Business Model, Go-to-Market, Team, The Ask, Vision) vs Client has 11-point arc (Title, Their Problem, Current Reality, Your Solution, How It Works, Before/After, Proof Points, Why Us, Pricing/ROI, Implementation, Next Steps)
  7. **Challenge label:** "🔍 Investor challenge" vs "🔍 Buyer challenge"
  8. **Assessment terminology:** Investor: "Story arc strength: Strong/Needs work/Weak", "Slides I'd fund on", "Kill question" vs Client: "Buyer conviction: Would sign/Needs work/Would pass", "Slides that would make the shortlist", "Kill objection"
  9. **Iteration prompt:** "narrative I'd take to a partner meeting" vs "pitch as a buyer would experience it"
  10. **Narrative document frontmatter:** Investor: `type: investor` vs Client: `type: client`, `target: {target_client}`; Client adds `## Target: {target_client}` section
  11. **Data Needs description:** Investor: "data points that would strengthen" vs Client: "proof points, ROI data, case studies"
  12. **Success/failure metrics:** Different framing (investor vs buyer perspective)
- **Merge strategy:** Substantial `{pitch_type}` conditionals. Slide arc and assessment framework are fully conditional. Challenge labels parameterized.

### Step 04: Data Layer

- **Status:** Minor differences (same structure, different framing)
- **Differences:**
  1. **Step goal:** "validation for each slide's narrative" vs "make each slide credible to a buyer"
  2. **Role reinforcement:** "The Investor ... where's the evidence?" vs "The Buyer ... where's the proof?"
  3. **Terminology shift:** "Data" (investor) vs "Proof" (client) throughout. Table headers: "Ideal Data Type" vs "Ideal Proof Type"
  4. **Extra client rule:** "Client pitches need different proof: ROI calculations, case studies, industry benchmarks, implementation success rates, customer satisfaction metrics"
  5. **Discussion headers:** "Data that would make this credible" vs "Proof a buyer would accept"
  6. **Source examples:** Investor: "industry reports (Gartner, McKinsey), public company filings, government statistics" vs Client: "customer success stories, industry reports, analyst reviews, G2/Capterra reviews"
  7. **Section 4 heading:** "Build Thesis and Counter-Thesis Data Lists" vs "Build Proof and Objection Lists"
  8. **Counter-thesis framing:** Investor: "COUNTER-THESIS — Data that could kill the deal" + "A VC partner will google these risks" vs Client: "BUYER OBJECTIONS — What a skeptical buyer would push back on" + "A procurement team will raise these" + extra list of common buyer objections
  9. **Research impact warning:** Different wording (VC vs buyer context)
  10. **Failure metrics:** Client adds "Focusing on investor-style data (TAM/SAM) instead of buyer-style proof (ROI, case studies)"
- **Merge strategy:** Terminology swaps via `{pitch_type}` conditionals. "Data" vs "Proof" framing, example sources, and counter-thesis/objections lists all conditional.

### Step 05: Research Prompt

- **Status:** Structural differences
- **Differences:**
  1. **Step goal:** "find data supporting the pitch thesis, one to find data that could kill it" vs "find proof points supporting the pitch, one to research buyer objections and competitive positioning"
  2. **Role reinforcement:** "The Investor crafting a research brief" vs "The Buyer crafting a research brief"
  3. **Rule about adversarial prompt:** "Counter-thesis prompt must be genuinely adversarial" vs "Objection research must be genuinely adversarial — surface real competitive threats"
  4. **Context document recommendations:** Investor: standard set. Client: adds "Competitive landscape document", "customer feedback or testimonial documents", "Pricing/unit economics documents"
  5. **Section 5 title:** "Generate Thesis-Support Research Prompt" vs "Generate Proof-Support Research Prompt"
  6. **Prompt structure:** Investor has 6 items. Client adds item 3 "Target Client Profile"
  7. **Research objectives framing:** Investor focuses on market/competitive/growth. Client focuses on industry benchmarks, case studies, ROI, implementation, client satisfaction, analyst opinions
  8. **Broadening examples:** Investor: TAM, competitor revenue, CAGR. Client: case studies, ROI benchmarks, buyer sentiment
  9. **Section 6 title:** "Generate Counter-Thesis Research Prompt" vs "Generate Objection Research Prompt"
  10. **Adversarial role:** "VC analyst conducting due diligence ... reasons NOT to invest" vs "procurement analyst conducting vendor evaluation ... reasons to choose a competitor or delay"
  11. **Research objectives:** Investor: business model risks, market headwinds, competitive threats, regulatory, technology, historical failures. Client: competitive alternatives, hidden costs/TCO, implementation failures, vendor lock-in, market maturity, security/compliance, abandonment reasons
  12. **Output frontmatter:** Investor: `type: investor`. Client: `type: client`, `target: {target_client}`
  13. **Section titles in saved doc:** "Investor Pitch Research Prompts" vs "Client Pitch Research Prompts"; "Thesis-Support" vs "Proof-Support"; "Counter-Thesis" vs "Buyer Objection"
  14. **Research impact warning:** Different wording
  15. **Failure metrics:** Client: "Using investor-focused research framing (TAM/SAM) instead of buyer-focused (ROI, TCO, case studies)"
- **Merge strategy:** Heavy `{pitch_type}` conditionals. Prompt structures, research objectives, and adversarial framing all switch. Client adds target client profile to prompt.

### Step 06: Structure

- **Status:** Minor differences
- **Differences:**
  1. **Role reinforcement:** "The Investor ... VCs will spend 2 minutes 40 seconds on" vs "The Buyer ... procurement team will evaluate ... buyers are busy and skeptical"
  2. **Total deck range:** "12-15 slides" vs "10-12 slides"
  3. **Extra client rule:** "ROI and proof slides should be early in the deck (buyers need conviction fast)"
  4. **Reference file instruction:** Investor: no qualifier. Client: "Focus on the client pitch section"
  5. **Table headers:** "Data Points" vs "Proof Points"
  6. **Slide pattern grouping:** Investor: "Hero, Data, Comparison, Story, Action". Client: "Hero, Problem, Solution, Proof, Comparison, Action"
  7. **User prompt:** "Does this structure work?" vs "Does this structure work for {target_client}?"
  8. **Success metrics:** Client adds "Proof slides positioned early enough to build conviction"
  9. **Failure metrics:** Investor: "Ignoring data layer annotations". Client: "Burying proof slides late in the deck"
- **Merge strategy:** `{pitch_type}` conditionals for slide count, slide patterns, and buyer-specific ordering guidance.

### Step 07: Generate HTML

- **Status:** Minor differences
- **Differences:**
  1. **Role reinforcement:** "The Investor ... Series A meeting. Every pixel matters. Design is compression, not decoration." vs "The Buyer ... six-figure contract. Every pixel matters. Client pitches must feel trustworthy and professional"
  2. **Extra client rule:** "Client decks should feel MORE conservative than investor decks — trust over excitement"
  3. **Visual direction note:** Client adds "Client decks benefit from a more conservative palette — blues, grays, whites convey trust"
  4. **Visual direction output:** Client adds "Tone: Professional/conservative (trust-first)" line
  5. **Image filename examples:** "slide-02-problem-data.png, slide-09-competition-matrix.png" vs "slide-02-client-problem.png, slide-07-proof-points.png"
  6. **Slide title examples:** Investor: "Companies lose $4.2M/year to manual processes" vs Client: "Manual processes cost your team 12 hours/week"
  7. **Verify output table:** Client adds "Tone: Professional/conservative — appropriate for B2B"
  8. **Menu summary:** Investor: "Type: Investor" vs Client: "Type: Client | Target: {target_client}"
  9. **Success metrics:** Investor: "Professional visual design with clear hierarchy". Client: "Professional, trust-first visual design"
  10. **Failure metrics:** Client: "Flashy/startup-y design inappropriate for B2B"
- **Merge strategy:** `{pitch_type}` conditionals for tone guidance, visual direction note, and menu summary. Most HTML generation logic is identical.

### Step 08: Images

- **Status:** Structural differences
- **Differences:**
  1. **Title:** "Visual Identity & Image Prompts" (investor) vs "Generate Image Prompts" (client) — investor version is significantly more comprehensive
  2. **Step goal:** Investor: "Integrate brand assets into the HTML, identify visual enhancement opportunities across all slides, add image references to the HTML, and generate prompts" vs Client: "Generate Google Nano Banana image prompts for each slide that needs imagery"
  3. **Investor has 9-section sequence:** Check brand assets → Integrate into HTML → Identify visual opportunities → Add image references → Generate prompts → Note photos → Save → Present summary → Menu
  4. **Client has 5-section sequence:** Audit HTML for image slots → Generate prompts → Save → Present summary → Menu
  5. **Investor includes brand asset integration:** Wordmark on cover/close/headers, CSS background patterns, photo placeholders — ALL absent from client
  6. **Investor has visual enhancement classification table** (which slides get backgrounds) — absent from client
  7. **Investor has CSS patterns** for `.slide-bg` and z-index layering — absent from client
  8. **Investor prompt structure is more detailed:** Includes opacity, slide background color, brand motif guidance
  9. **Client prompt style:** "professional, corporate, business-appropriate" vs Investor: "professional, clean, minimal"
  10. **Image style guidance:** Investor allows abstract textures, brand metaphors. Client: "no whimsical illustrations or abstract art ... corporate photography, clean diagrams"
  11. **Saved document header:** Investor: `{pitch_type} Pitch`. Client: `Client Pitch for {target_client}`
  12. **Success/failure metrics:** Investor is much more extensive (brand integration, visual opportunities, CSS patterns). Client focuses on prompt quality and B2B appropriateness.
- **Merge strategy:** Use investor version as base (it's a superset). Add `{pitch_type}` conditionals for style guidance (conservative B2B for client, more expressive for investor). The visual enhancement and brand integration sections apply to both types. Client's more limited version was likely an oversight — visual polish benefits client decks too.

### Step 09: Synthesis

- **Status:** Minor differences
- **Differences:**
  1. **Step goal:** "investor pitch package" vs "client pitch package"
  2. **Package emoji/label:** "💰 Investor Pitch Package" vs "🤝 Client Pitch Package"
  3. **Client adds `Target: {target_client}` line** to summary
  4. **Deliverable descriptions:** "Stress-tested" vs "Buyer-tested"; "thesis + counter-thesis" vs "proof + objections"
  5. **Quality checks:** Investor: "Narrative stress-tested", "Counter-thesis risks addressed", "12-15 slides", "Strongest slides front-loaded", "The Ask is clear" vs Client: "Narrative framed from buyer's perspective", "Buyer objections addressed", "10-12 slides", "ROI/proof slides early", "Professional trust-first design", "Clear CTA/next steps", "No feature dumps"
  6. **Next steps:** Investor: "thesis + counter-thesis" terminology. Client: "proof + objections", adds step 3 "Prepare objection responses", step 9 "Tailor for specific client"
  7. **Success metrics:** Client adds "Objection preparation called out explicitly"
  8. **Failure metrics:** Client adds "Forgetting to mention objection preparation"
- **Merge strategy:** `{pitch_type}` conditionals for terminology, quality checks, and next steps. Both share same overall structure.

---

## Edit Mode Comparison

### Step E01: Load

- **Status:** Minor differences
- **Differences:**
  1. **Title:** "Load Existing Pitch Deck" vs "Load Existing Client Pitch Deck"
  2. **Role reinforcement:** "The Investor ... more fundable" vs "The Buyer ... procurement committee review"
  3. **Output folder path:** `_fundraising/pitch-deck` vs `_clients/pitch-deck`
  4. **Edit options:** Client adds "Proof Update" and "Client Tailoring" options; Investor has "Data Update" instead of "Proof Update"
- **Merge strategy:** Simple `{pitch_type}` conditionals for path, role, and edit menu options.

### Step E02: Edit

- **Status:** Minor differences
- **Differences:**
  1. **Step goal:** "existing pitch deck" vs "existing client pitch deck"
  2. **Role reinforcement:** "The Investor ... more fundable ... clarity or weakens the narrative" vs "The Buyer ... procurement committee ... clarity or weakens buyer conviction"
  3. **Slide count range:** "12-15" vs "10-12"
  4. **Edit operations:** Client adds "Proof updates" and "Client tailoring" sections. Investor has "Data updates" instead.
- **Merge strategy:** Simple `{pitch_type}` conditionals for role, slide count, and edit operation terminology.

---

## Summary

| Step | Divergence Level | Key Parameterization Needs |
|------|-----------------|---------------------------|
| workflow.md | Minor | Name, description, outputFolder, role description |
| Step 01 | Structural | Client has extra "Understand Target Client" section |
| Step 02 | Structural | Entirely different context-distill queries and brief structure |
| Step 03 | Structural | Different slide arcs (13 vs 11 slides), different assessment framework |
| Step 04 | Minor | "Data" vs "Proof" terminology, different examples |
| Step 05 | Structural | Different prompt structures, research objectives, adversarial framing |
| Step 06 | Minor | Slide count range, slide pattern categories, ordering guidance |
| Step 07 | Minor | Tone guidance, visual direction, conservative vs expressive |
| Step 08 | Structural | Investor is superset — use as base, add client style conditionals |
| Step 09 | Minor | Terminology, quality checks, next steps |
| E01 | Minor | Path, role, edit menu options |
| E02 | Minor | Role, slide count, edit operation types |

**No unmergeable differences found.** All differences are handleable via `{pitch_type}` conditional blocks.
