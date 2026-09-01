---
name: meeting-prep
default-execution-mode: interactive
four-letters: mpre
---

# meeting-prep — the workflow

**Default execution mode.** `interactive` — declared above. A goal created from this workflow is born with it. A per-goal value in the creation request overrides this default.

**Four letters (`mpre`).** The prefix every seat-id in `meeting-prep.csv` shares.

**Goal.** Produce a print-ready strategic cheat sheet for an upcoming meeting.

**Scope.** Inputs are meeting basics from the user (topic, other party, why a cheat sheet is wanted). Output is one cheat sheet, adapted to the meeting type and written in the language of the sitting. The eight files in `data/` are type skeletons loaded by classify and generate; they are not skills. This workflow NEVER summarises a past meeting.

**The chain (`meeting-prep.csv` is the DAG).** Three seats, serial, guard-free:

1. `mpre-classify` — capture basics, classify type, one workspace-read ask, load type data.
2. `mpre-discover` — guided discovery against the type-data questions; offer research when an unknown appears.
3. `mpre-generate` — write the cheat sheet from the type skeleton and discovery, present the draft, land the file.

**Filename.** `YYYY-MM-DD-{topic}-cheatsheet.md` — the date is the meeting date, not today. Path comes from the caller / goal seed. If neither supplied a directory, ask once for the destination directory and apply this filename there.

**Standing rules.** NEVER generate a cheat sheet before discovery has covered the mandatory dimensions. NEVER pad with generic advice — every line MUST be specific to this meeting. ALWAYS write in the language the user has been speaking. ALWAYS prefer tables over essays. The "what NOT to say" and calibration sections MUST be honest.

## Classify

Ask only what the sitting has not already given:

| Question | Purpose |
|----------|---------|
| What is this meeting about? | Topic |
| Who is the other party? (person, company, or both) | Context-sweep target |
| Why a cheat sheet for this one? | The real preparation need |

Classify into one type:

| Type | Slug | Primary signal |
|------|------|----------------|
| Sales / Demo | `sales` | Presenting a product or service to a potential buyer |
| Investor | `investor` | Pitching to or meeting a fund, angel, or advisor about funding |
| Negotiation | `negotiation` | Terms, pricing, contracts, deal-making with a known counterparty |
| Partnership | `partnership` | Exploring or formalizing collaboration between organizations |
| Discovery | `discovery` | Learning from someone — research, user interviews, expert consultation |
| Advisory / Board | `advisory` | Mentor, advisor, or board member for guidance |
| Hiring / Interview | `hiring` | Evaluating or being evaluated for a role |
| Crisis / Damage Control | `crisis` | After something went wrong — trust repair, incident response |

Present the type and a 1–2 sentence why. If the user disagrees, reclassify.

Search the workspace for files about the other party (names, folders, notes, prior cheat sheets, correspondence). Present a table of hits — path and why it might matter — and ask **once** which to read (all / numbers / none). Read only those. If nothing is found, say so and continue.

Load `data/type-{slug}.md` from this workflow folder. Write `planning/meeting-class.md` (first line `MEETING-CLASS`) with type, topic, other party, why, files read, and the type-data path. Then discover starts — no extra confirmation.

## Discover

Review what classify already holds. Use the loaded type file's discovery questions as a skeleton, not a script.

**Mandatory dimensions** (cover all, any order):

1. Objectives — what the user wants from this meeting
2. Relationship context — history between the parties
3. Strategy — approach, impression, what to avoid
4. Logistics — date, time, format, participants

Acknowledge what is already known; go deep when the user opens up; batch 2–3 questions; NEVER fire a rigid one-by-one list.

When an unknown appears (a company, person, fund, product, term, or fact the objective depends on): name it, ask whether to research it, and only then search. Present findings as a few bullets, facts separated from inference. If research contradicts the user, surface the discrepancy.

After the dimensions are covered, show a gap table (covered / partial / missing) and fill the holes. Ask if anything else belongs in the cheat sheet, then generate.

Write `planning/meeting-discovery.md` (first line `MEETING-DISCOVERY`) with the four dimensions, type-specific notes, research, and remaining gaps.

## Generate

Using the type file's output skeleton and all discovery context, produce the complete cheat sheet.

| Rule | Detail |
|------|--------|
| Specificity | Every item is for this meeting, this party, this context. |
| Language match | Same language as the sitting. |
| Actionable | Every section helps the user do something — prepare, say, avoid, decide. |
| Honest calibration | "What NOT to say" is blunt. If the user is tempted to oversell, say so. |
| Skeleton adaptation | Include skeleton sections that have content; skip ones that do not apply; add a section when discovery revealed something the skeleton lacks. |
| Print-ready | Glance reference — tables, direct language, no fluff. |

Present the full draft. Incorporate feedback until the user approves. Then write `planning/cheatsheet.md` (first line `CHEATSHEET`) and land the same content at the caller-supplied path under the filename convention above. Report the saved path, meeting date, and type.
