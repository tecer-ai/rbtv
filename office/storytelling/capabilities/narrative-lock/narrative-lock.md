---
id: narrative-lock
description: Lock one audience-relative story spine of beats — not slides, not pixels — before any visual work. Interactive; the owner is live. Output is the gated narrative-lock artifact.
inputs: run seed (brief, source materials, stated audience as a role never a canned mode id); brand-pack voice resolved at runtime from `.rbtv/config/office/` with guided setup when the pack is absent; the owner, live; decision-research findings when the deciding spine has already run
outcome: owner and this capability agree the audience-relative lock definition is met, and `narrative-lock.md` carries all eight required sections
outputs: the `narrative-lock.md` artifact (eight sections, completeness floor below); zero or more decision-research briefs emitted at the wait point, pointed from Briefs emitted
---

# narrative-lock

Make the audience believe or do one thing. Lock that as a story spine of beats. Visual form is not this role.

Embody `prompts/strategist.md` for the whole run. This capability does not run headless — the owner is live.

## Inputs

- **Run seed** — brief, source materials, stated audience as a role. NEVER treat audience as a canned mode id to resolve.
- **Brand-pack voice** — resolve at runtime from `.rbtv/config/office/`. When the pack is absent, run guided setup to capture voice; NEVER invent a voice.
- **Owner, live** — excavation and confirmation happen with the owner. NEVER run this capability without them.
- **Decision-research findings** — when the deciding spine has already run, consume them here. Do not re-emit those briefs.

A prior artifact handed as reference is content input only — extract claims and copy, NEVER a restyling base or a structure to inherit. Blank-slate versus revise is the host's routing, not this capability's job.

## Procedure

Run the five steps in order. After step 3 the procedure names a wait point; resume at step 4 when findings are in hand. A pause inside one sitting and a split across two sittings that meet at that point are both legal.

### 1. Audience

Dedicated early step. Probe until the seat is specific: role, expertise, what they already know, resistance. Refuse "everyone" and "to inform". Inventory materials already in hand. Do not ask questions the seed already answers.

Agree with the owner, before any later freeze, what "locked" means for this audience (see Lock definition).

### 2. Interview

Excavation, not a checklist. Work friction → stakes → claim → reader transformation → doubt. Follow-ups adapt to what the owner just said. A messy dump is welcome; the conversation is the thinking. This is a procedure step, never a part-id or skill name.

### 3. Decision-research briefs

When load-bearing claims are unevidenced, emit the deciding spine as self-contained briefs (schema lives in the `research-brief` capability): themes → options → segments → implications → insights → connections. Types that decide (`audience-intel`, `competitive-context`) belong here. Fill-research (`content-facts`) waits until after the lock — NEVER emit it as part of this step.

**Wait point:** emit those briefs, then wait for findings before freezing the thesis. Resume at step 4 when findings are in hand. If no load-bearing claim is unevidenced, or findings are already in hand at entry, do not wait.

Map returned findings to their keys. Flag weak or conflicting sources. Remaining unsourced external-facing claims become Open data gaps — the claim is blocked, NEVER invented.

### 4. Theme / structure

Convert the raw dump into the annotated spine. Each beat carries its point-title, its role in the arc, and a claim / observation / opinion annotation. Challenge every junction: does B follow from A? The owner confirms the spine before step 5.

### 5. Emit `narrative-lock.md`

Write the artifact with all eight sections below. Challenge each beat from the audience seat; every challenge MUST pair with a concrete alternative. Apply `ai-anti-patterns` to titles, points, and notes. Titles state the point.

Then stop.

## Output contract — `narrative-lock.md`

The artifact this run produces at runtime. A lock missing any required section is incomplete and does not pass gate 1.

| Section | What it holds |
|---|---|
| Audience | Specific seat: role, expertise, what they already know, resistance. "Everyone" / "to inform" refused. |
| Objective | The single belief or action the piece MUST produce. |
| Interview seed | Friction, preliminary claim (or explicit exploration direction), stakes (why now), reader transformation, known vulnerabilities. |
| Thesis | One sentence the whole piece MUST make true. |
| Narrative spine | Ordered story beats — not slides. Each beat: point-title (the takeaway, never a label), role in the arc, claims vs observations vs opinions, per-datum communication intent plus owner-supplied source or gap. |
| Narrative assessment | Arc strength, beats that land, beats that need work, missing, the kill question — and whether the lock answers it. |
| Open data gaps | Every unsourced external-facing claim; the claim is blocked, never invented. |
| Briefs emitted | Pointers to any research briefs this sitting authored. |

One beat, one point. Two points on one beat: split or rethink. NEVER freeze a thesis the wait point still owes findings for.

## Lock definition

Audience-relative. Owner and this capability BOTH agree it is met before the artifact is gated.

- Investor: defensible in a partner meeting.
- Buyer: survives a procurement review.
- Other audiences: the kill question is answered.

## Hard stops

- NEVER use design language: no layout, colour, type, component, or chart-type choice. NEVER a palette, typeface, font-family, hex colour, grid, motif, chart style, or component library.
- NEVER assign slide numbers. Grouping beats into slides belongs to `visual-strategist`.
- NEVER produce or edit HTML. This role NEVER emits `<html`. Building, rebuilding, or "just applying a fix" in HTML is a role breach.
- NEVER fabricate, infer, or invent a number. Every external-facing number is owner-sourced. An unsourced claim BLOCKS; it is listed under Open data gaps.
- NEVER proceed to visual form. The lock is the end of this capability.
