---
stepNumber: 2
stepName: 'context-gather'
nextStepFile: ./step-03-narrative.md
---

# Step 02: Context Gathering

**Progress: Step 2 of 10** — Next: Narrative Draft

---

## STEP GOAL

Gather pitch-relevant context from two sources derived from the resolved output path:
1. **Entity directory** — the client or investor entity folder (root-level `.md` files only)
2. **Brand directory** — the project's brand folder for visual identity and messaging guidelines

If no documents are found, gather context conversationally.

---

## MANDATORY EXECUTION RULES

### Universal Rules

- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly

### Role Reinforcement

**If pitch_type = investor:**
You are The Investor mining documents for the strongest possible pitch material. Think like a partner reviewing a deal memo — what would make you champion this in the Monday meeting?

**If pitch_type = client:**
You are The Buyer mining documents for the content that would convince a procurement committee. Think like a VP evaluating a vendor — what would make you put this on the shortlist?

### Step-Specific Rules

- Read `.md` files at the ROOT level of each directory only — never descend into subdirectories
- Do NOT ask the user questions already answered in the documents
- Accumulate findings into a structured pitch brief

---

## MANDATORY SEQUENCE

### 1. Identify the Entity Directory

From the resolved output path (`{output_folder}`), navigate up to the **entity directory** — the nearest ancestor that represents the entity this pitch targets.

The entity directory is the folder that represents the client, fund, or target entity — not a date-stamped or objective-specific subfolder. Identify it by finding the ancestor whose name matches the entity variable resolved during Step 01 ({target_client}, fund name, etc.).

List all `.md` files at the root of the entity directory (non-recursive). If none are found, note this — context will be gathered conversationally in Section 4.

### 2. Resolve and Read Brand Context

Read the workspace CLAUDE.md for a `brand` route in the `## File Routing` block.

If a brand route exists:
- Navigate to the resolved brand directory
- List all `.md` files at the root level (non-recursive)
- Read each file to extract: visual identity, color palette, typography, tone of voice, brand assets, messaging guidelines

If no brand route exists: skip silently. Brand context is valuable but not blocking.

### 3. Compile Pitch Brief

Read all discovered `.md` files and compile findings into a pitch brief.

**If pitch_type = investor:**
```
## Pitch Brief: {project_name}
### Type: Investor

#### Problem
[Pain points, who experiences them, quantified impact]

#### Solution
[Key differentiators, how it works — max 3 differentiators]

#### Market Size
[TAM/SAM/SOM if available, market data]

#### Traction
[Validation, metrics, proof points with dates]

#### Unit Economics
[Pricing, margins, CAC, LTV if available]

#### Competitive Position
[Named competitors, differentiation]

#### Brand & Messaging
[Brand identity, visual direction, key messages — from brand docs]

#### Why Now
[Market trends, timing evidence]

#### Team
[Founder/team info if available]

#### Gaps
[What's missing that we need to ask the founder about]
```

**If pitch_type = client:**
```
## Client Pitch Brief: {project_name}
### Target: {target_client}

#### Their Problem
[The client's specific pain — in THEIR language, not yours]

#### Current Solution / Status Quo
[What they use today and why it's insufficient]

#### Your Solution
[What you do for them, concrete benefits]

#### How It Works
[Workflow, process, integration points]

#### Proof Points
[Testimonials, case studies, metrics, pilot results]

#### Competitive Alternatives
[What else they could buy and why you're different]

#### Pricing & ROI
[Plans, pricing, ROI framework if available]

#### Brand & Messaging
[Trust signals, positioning, tone — from brand docs]

#### Gaps
[What's missing that we need to ask about]
```

Populate each section from what the documents contain. Leave sections empty (with a note) when no relevant content was found — these become gaps.

If NO documents were found at all (no entity directory files, no brand files), skip the brief and proceed directly to Section 4.

### 4. Present Findings and Fill Gaps

**If documents were found:**
- Present the compiled pitch brief
- Highlight the **Gaps** section
- Ask ONLY for the missing information
- Wait for user response. Update the pitch brief with their answers.

**If NO documents were found:**
Gather context conversationally:

**If pitch_type = investor:** Ask (only what's missing from conversation context):
- One-line description of what the company does
- Stage (pre-seed, seed, Series A, etc.)
- How much you're raising and what for
- Key differentiator or "why now"
- Target market and size estimate
- Any traction or validation data

**If pitch_type = client:** Ask (only what's missing):
- One-line description of what the company does
- Key differentiator vs. what the client uses today
- Price range or pricing model
- Any proof points or case studies

Wait for user response. Compile into a pitch brief using the template from Section 3.

### 5. Present Menu

**Select an Option:**
- **[C] Continue** — proceed to narrative drafting
- **[X] Exit** — exit workflow

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:
1. Load `{nextStepFile}` and carry the pitch brief forward as context

ONLY when **[X] Exit** is selected:
1. Confirm exit and end workflow

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:**
- Entity directory identified from output path and root-level `.md` files read
- Brand context loaded (if route exists in File Routing)
- Pitch brief compiled from discovered documents
- Gaps identified and filled through targeted questions
- User confirms brief accuracy

❌ **FAILURE:**
- Hardcoding paths to specific directories or documents
- Reading files recursively into subdirectories
- Asking questions already answered in discovered documents
- Fabricating content not found in documents
- Skipping brand context when a route exists
