---
name: presentation
default-execution-mode: interactive
---

# presentation — the workflow

**Default execution mode.** `interactive` — declared above, in this workflow's own scaffolding. It is
the value a goal created from this workflow is BORN with: goal creation writes it into the goal's
`execution-mode` file, and the control plane gates every agent-initiated owner contact on it. Declared
rather than left to derivation because three of this chain's fifteen seats are OWNER GATES whose whole
remit is reaching the human, and a gate that cannot reach the owner is not a gate. The pair that lets a
gate fire is the seat's own `human-interactive: yes` AND this mode; neither half works alone. A
per-goal value supplied in the creation request overrides this default; this is the floor, never a lock.

**Goal.** Turn a raw ask — a brief, an audience, whatever materials are already in hand — into a
finished presentation: an HTML deck and its matching PDF, built on a narrative the owner locked before
any design existed, in the owner's own brand, verified twice before the owner is asked to accept it.

**Scope.** This workflow CHAINS capabilities its component and the module's sibling components already
own — narrative excavation, research briefs, visual strategy, design extraction and checking, HTML
standards, deck production, conversion. It defines no capability of its own, and it copies none: every
stage binds its instruments by load at run time. Its V1 sinks are HTML and PDF, and only those. It does
not review third-party HTML, does not summarize meetings, does not write email, and does not build a
site or an app — those are other parts and other workflows.

## The production model — load-bearing at every stage that touches a page

Every page in this run is **agent-authored HTML**: an agent writes the markup, and the look and the
layout come from that agent applying the HTML standards library's Presentation profile plus the brand
pack. There is no schema and no deterministic builder in this chain. That is why the deterministic
check here means *source CSS, SVG and HTML measured against brand-pack tokens and the library profile*
— under a builder model the same phrase would mean checking a schema and the builder's output, because
the agent would never have written any CSS. The two readings are not interchangeable, and flattening
them is a defect, not a simplification.

## The chain (`presentation.csv` is the DAG)

Fifteen seats. Three owner gates, and only three. Guards on the edges are data, evaluated
deterministically against the predecessor's validated output — never a judgement made at an edge.

1. `pres-kickoff` — resolve the brand pack (or run guided setup; never a silent training-mean brand),
   inventory the materials, record the stakes, write the run brief.
2. `pres-excavate` — sitting one of the narrative-lock capability: pin the audience until it is
   specific, excavate friction to stakes to claim to transformation to doubt, and emit the research
   briefs the next two seats execute.
3. `pres-intel` ∥ `pres-spine` — the two research strands, in parallel and each guarded off its brief
   set. The spine walks themes, options, segments, implications, insights, connections in one seat as
   brief-sized chunks: research that DECIDES, before research that fills.
4. `pres-lock` — **GATE 1.** Sitting two of the same capability. The locked narrative is the gate; a
   lock missing a required section does not pass. The chain is acyclic, so the wait the capability
   itself names is two sittings around the research, never a cycle and never a second role.
5. `pres-fill` ∥ the visual strand — fill research runs from the lock all the way to the deck build,
   overlapping gate 2. It fans its per-beat probes IN PROCESS, one subfolder per probe, because the
   section count is unknown when this graph is written and a static DAG cannot mint a row per beat.
6. `pres-vstrat` → `pres-vizref` (guarded) → `pres-direct` — the visual strand runs SEQUENTIALLY. The
   designer consumes the visual-communication plan and must not start without it, so these three are
   never parallelized with one another.
7. `pres-blueprint` — **GATE 2.** Slide list, visual plan and 2-3 art-direction options presented as
   ONE gate; the owner picks a direction. The picked brief becomes the visual contract. No deck is
   rendered here.
8. `pres-build` — the deck, slice by slice, over a local HTTP server, plus the PDF from the converter's
   print path.
9. `pres-check` → `pres-inspect` — verification in two mechanisms, in this order: cheap scripts first,
   then a fresh-context reviewer looking at actual screenshots. Fresh eyes ALWAYS run before gate 3, so
   the owner meets a floor-raised deck rather than a raw first pass.
10. `pres-final` — **GATE 3.** The owner reviews the rendered deck headed and accepts, or bounces with
    notes. Taste gate.
11. `pres-handover` — guarded on that acceptance: the deck, a rationale document and the asset library
    as one package. Always OFFERED, never forced; skipping it is a valid end to the run.

## Loop-back — into the build, never back into the narrative

A failure at `pres-check`, at `pres-inspect`, or a bounce at gate 3 re-enters at `pres-build` and runs
forward through every checker below the seat that failed. The patch is SURGICAL: only the flagged
slides change and every other slide stays byte-identical. The lock, the visual plan, the art direction
and gate 2 are not re-run — the graph carries no edge back to them, and it is acyclic by contract.
Each checker names ITSELF in its relaunch set, because a loop that re-fires the fixer without the
checker never closes.

A rethink at the level of the MESSAGE is not a loop. It is a FAIL to the goal's leader chair with a
recommendation, and — if the owner wants it — a new goal. Three failure modes route that way by design:
a fill finding that falsifies a must-have locked claim, roughly three bounces on one slide, and a
second wholesale rejection of the art direction after the designer has already regenerated once.

## What a run needs from its caller

The brief and the audience — a real role, not a canned mode id — are required; materials, a prior
artifact and the stakes are optional. A prior artifact is content input ONLY and is never a restyling
base. Everything else this workflow needs is runtime configuration it resolves itself: the brand pack
(voice, palette, type, templates, glossary) comes from the workspace office config root, with guided
setup when it is absent, and the canvas and typographic numbers come from the library's Presentation
profile at run time. None of those are parameters, and none are baked into these files.
