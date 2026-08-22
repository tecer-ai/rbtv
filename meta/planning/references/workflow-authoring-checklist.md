---
description: Read at the moment of authoring or amending a workflow's seat declarations — the six declarations a produced seat must carry before it is registered, each one a wall the materializer or the sandbox enforces later.
tags: [planning]
---

# Workflow-authoring checklist — the six declarations a produced seat must carry

You are authoring seats for a workflow this run PRODUCES (an optimize, port, or scaffold output, or an ad-hoc goal's taskforce). Each row below is a declaration the produced seat carries, and each one is a wall somewhere downstream: the materializer refuses at generation time, or the kernel answers `EROFS` at run time. Author them here and the wall is never met. Companions: `component-anatomy.md` (which files exist), `workflow-anatomy.md` (the graph), `file-prompt.md` (the frontmatter card), `kind-permissions.md` / `kind-restrictions.md` (the two bound sections).

## 1 — ONE declared output per seat (`goal-writes`)

Every seat may APPEND to the five write-if-something ledgers in its goal folder — `issues.md` · `decisions.md` · `doubts.md` · `gotchas.md` · `ideas.md`. That grant is automatic; never declare it, never restate it as a permission.

On top of it a seat declares AT MOST ONE goal-folder output, in the seat catalog's `goal-writes` column: one path RELATIVE TO THE GOAL FOLDER (not the workspace — that is `rw-paths`). A seat whose product stays in its own seat folder declares nothing, and that empty column is a statement, not an omission.

- Ground truth is refused and stays refused: `sessions.csv`, `state.csv`, another seat's folder, `seat.md`. An absolute path or one climbing out with `..` is refused too.
- A declared path that does not exist yet is CREATED EMPTY at spawn, so a role may name a product nothing has produced. Only the empty file and at most its parent directory are created — never content, never a header — so a consumer that needs a header still needs the upstream seat that writes one.
- A MULTI-SEAT PHASE HANDS ARTIFACTS ACROSS THE GOAL'S `planning/` WORKSPACE — the one goal subtree the cage opens read-write to every seat (owner ruling d-s31-planning-workspace-shared-rw). A product no successor reads stays in the seat's own folder; a product a successor reads goes under `planning/` at a literal path both units name. A peer's SEAT FOLDER is absent under the seats tmpfs — never route a cross-seat read through one. The planning component's own check swarm is the live instance: seven `planning/current/findings-<dimension>.md`, read by `plan-check-assembler`.
- A CONSUMER MUST NOT TREAT EXISTENCE AS PRODUCTION. A declared or workspace file can exist EMPTY from spawn onward, so "the file exists" proves nothing. Every produced artifact carries a first-line marker its consumer checks (the check swarm's is the PASS|FAIL verdict line); an empty or markerless file is a non-report, never a pass.
- Only ONE. A role that needs two goal-folder products is two roles, or one product it has not named yet.
- A SEAT THAT PRODUCES NO FILE SAYS SO, in its prompt's `<io-spec>` `## Outputs`: `- Schema: chat …`, the one typed non-file output (D36, 2026-08-20). A verdict on the bus, an answer, a `queue-request` — the rows ARE the product. Without it the seat's every `done` is refused as unverifiable; with it, the check-out admits the `done` and records `none-declared`. `goal-writes` stays empty either way — the two columns answer different questions (what it may WRITE vs what it must have PRODUCED).
- A product landing OUTSIDE the goal folder is `rw-paths` on the prompt frontmatter (a YAML list of workspace-relative paths), never `goal-writes`. Name a path that exists at launch — a parent, if the product is new. Spawn still skips a missing path.

## 2 — Every instrument declared in `exposes:` AND described in `<resources>`

An occupant never discovers its means. Anything the seat must reach is declared in its prompt frontmatter `exposes:`, keyed by the method its `exposure.csv` row carries — `skill` · `command` · `rule` · `hook` · `sub-agent` · `path`. Prose in `<resources>` says WHEN and WHY; `exposes:` is what makes the thing REACHABLE inside a sandbox. Prose alone left a caged seat ordered to check in with no `coordinate` it could run.

**Declared is not described (owner-ruled 2026-08-12).** Every `exposes:` entry of method `path` (a CLI), `skill`, or `sub-agent` ALSO gets its OWN bullet in the prompt's `<resources>` section: the part-id, then AT MOST 280 characters saying how the occupant uses it — when to reach for it, what it hands back, and the one caveat it would otherwise learn the hard way. The 280 is a ceiling, not a target. The two are not a duplication and neither substitutes: the frontmatter is read by the MATERIALIZER, which binds and mints the instrument; the bullet is read by the OCCUPANT, which decides whether this is the moment to use it. An entry with no bullet is a means the occupant has to discover — the exact failure this checklist exists to prevent.

- `command`, `rule`, and `hook` entries get NO bullet: they arrive as standing behaviour the occupant is already under, not as something it chooses to invoke.
- ONE exemption inside `path`: the standing `rbtv:ignite/team-kit/coordinate` checkout grant, which belongs to the run protocol and never to the role. Any use of `coordinate` BEYOND checkout — an owner-channel ask, a fail-status query, a registration act — is described like every other instrument.
- A `sub-agent` bullet says what the dispatched definition is FOR and what comes back, so the occupant knows what to hand it and what it may not delegate — never just that the definition exists.
- Where a seat holds an instrument no step of its procedure uses, the defect is the GRANT, not the missing bullet: delete the entry.
- One shape, so a reader scans a `<resources>` section instead of reading it: `` - `<part-id>` <what it is> — <what it gives the occupant>. <when to reach for it, and the caveat>. ``

- A CLI is the `path` group. Reference grammar by segment count: `part` (this component) · `component/part` (sibling, same module) · `module/component/part` (another module). An `rbtv:`-prefixed reference resolves against the rbtv repo tree instead — how a mirror-resident seat reaches a repo-resident tool.
- A tool OUTSIDE the component and outside the repo — a workspace tool — is reached by a `method=path` row whose `entry-point` carries the `ws:` prefix: a path from the WORKSPACE ROOT, the first ancestor holding `.rbtv/config/` (`ws:3-resources/tools/stools/stools.py` — the `stools` grant on this component's interviewer is the live instance). The row is the prerequisite; the seat's `exposes:` is the grant. `ws:` is legal on `method=path` rows only; every other method's entry-point is copied out of the component by the installer, and a workspace path is not inside it.
- An entry-point that climbs out with `..` is REFUSED at materialization, on every method, prefixed or not — the same refusal rule 1 applies to `goal-writes`, and for the same reason: counting directories out of a component is a path that breaks the moment the component moves. `ws:` is the one sanctioned way out, so an old example cannot reintroduce the climb by being copied.
- The manifest is the one home of the part→method binding: a group key disagreeing with the row's `method` column is refused at materialization.

## 3 — Mark a user-facing seat interactive

A seat whose ROLE includes reaching the human declares `human-interactive: yes` plus its typed `fallback` (`park` · `default-and-disclose` · `block-and-queue`), and its manifest row carries Modality `interactive`. Marking it is what auto-attaches the owner-facing message standard (`master-agent/slack-message-format`) as a skill, so every message the seat writes is already Slack-shaped, asks are separated from notes, and nothing dumps a file into chat.

Contact fires only when the flag AND the goal's execution mode agree, so the autonomous arm is the path and interaction is the enhancement: the procedure must CARRY the autonomous behaviour in its own words, never just name the arm.

## 4 — The seat-folder standard, by name

A produced seat's folder surfaces are FIXED NAMES so a human and the next sitting find the files where they expect them: `memory.md` (the seat's dated working state) · the five ledgers in the GOAL folder · the `goal-writes` path for the role's one product · `downloads/` · `scratchpad/` · `outputs/`. The three folders are CREATED THE FIRST TIME THEY ARE NEEDED — never scaffolded speculatively, never renamed, never a fourth name minted for one of them.

An IN-PROCESS probe a seat fans out (a researcher, a diagnoser, a per-seat mechanization probe) shares the launching seat's cage and therefore its folder — so each dispatch gets its OWN subfolder of the scratchpad, `scratchpad/probes/<short-name>-<n>/`, where `<short-name>` names the probe's subject (the seat id, for a per-seat probe) and `<n>` is its ordinal in that fan-out. One folder per dispatch, created when first needed like the three above it: concurrent probes then cannot collide on a filename, and every returned fact traces to the dispatch that observed it. Nothing else in the seat folder is probe-writable, and no probe writes at the folder root.

## 5 — No owner-specific value is ever hardcoded

A workflow is a program; an owner's channel id, vault path, account, host, or credential is run-time configuration. Those values live under `.rbtv/config/modules/<module>/<component>/…` and are read at run time — never typed into a prompt, a task, a manifest, or a seat definition. A produced workflow carrying one is not portable and is not finished.

## 6 — The definition of done gets a completeness review

A definition of done is not done when it is falsifiable — it is done when it is falsifiable AND complete. Author the flow so the ratified definition of done passes an adversarial completeness review before anything is split, structured, or staffed: missing actors, unstated inputs, undefined failure behaviour, implicit assumptions, and the edge cases the happy path hides (two of a thing inside one window, an item present in neither source, duplicates). This component seats that review at `plan-completeness-reviewer`; a workflow you produce carries the same expectation.

## Loop routes — `on-fail-relaunch`, declared only where a loop exists

The seat catalog's ninth column. It is the CALLER'S OWN declaration of who is re-fired when THIS seat records a FAIL, and it is read at two doors: the verdict verb mints the relaunch grants for the seats it names, and `route-fail` reads it when a seat routes a FAIL by hand. Empty is the normal state and a statement, not an omission — an UNDECLARED fail goes to the goal's `leader` chair, which is a chair rather than a silence.

- Declare it on the seat that ISSUES the verdict, never on the seat that is re-fired. The live instance is the forge's `forg-judge`, whose cell reads `forg-builder,forg-judge` — the builder to fix the finding, and the judge ITSELF to re-try the contract afterwards. A loop that re-fires the fixer without the checker never closes.
- Every entry names a SEAT of the same workflow's `seats.csv`, spelled exactly. Syntax is checked at every door and EXISTENCE at none until run time: a task id or a milestone id in this cell is a perfectly well-formed name that names nobody, and it is exactly how a routed FAIL reached no one.
- A seat that holds no loop leaves it EMPTY. Never fill it with the `leader`, a staff chair, or the seat's own successor "for safety": the fallback already goes to the `leader`, and a staff chair has no session to relaunch.
- The two doors hand the re-fired seat DIFFERENT things, so author the FAIL body for the weaker one: `route-fail` writes a payload its target's next boot prompt folds in, while the verdict verb's loop re-fire mints grants ONLY — no payload — leaving the verdict body on the log as the whole instruction that seat gets.

## Stop rule

A declaration this checklist cannot express — a seat needing two goal-folder outputs, an instrument no exposure method fits, a value that is neither authored nor configurable: STOP and surface it. The walls are the contract, not a suggestion.
