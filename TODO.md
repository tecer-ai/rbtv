# RBTV — Open Items

Post-standalone items carried over from the intermediary plan execution (2026-04-17). These are known gaps or unverified areas — not bugs in the shipped install.

## Agents are not admin-only — fix create-component 404

Agents under `agents/<name>/<name>.md` are NOT admin agents. They are the personas loaded by many skills and commands (Ana, DomCobb, Fernando, Paul, Leo, Roelof, Vivian, George Orwell). When `/rbtv-create-component` runs, it loads Fernando's persona, which then tries to load the create-component workflow.

Problem: `workflows/component-creation/workflow.md` does NOT exist. The directory has `templates/` and `data/` but no workflow.md. Task 7 of the plan assumed it existed. First invocation of `/rbtv-create-component` will 404.

Action: write `workflows/component-creation/workflow.md` from scratch. It must orchestrate Fernando's component-creation flow (ask publish-vs-local, walk the user through agent/skill/workflow/task templates in `templates/`, consume `data/component-patterns.md` and `data/bmad-architecture.md`).

## Review items from execution

### 1. `{output_path}` dead placeholders (Phase 4)

The Phase 4 subagent replaced all `{bmad_output}` occurrences (~120) with `{output_path}`. Per D7, output paths are resolved at runtime by the `rbtv-output-resolution` rule — there is NO baked placeholder. Every `{output_path}/...` in RBTV is a dead string that never gets substituted.

Action: `grep -rn "{output_path}" "3. Resources/rbtv"` and, per match, either delete the surrounding sentence or rewrite to reference the resolution rule (e.g., "Output location resolved per the `rbtv-output-resolution` rule").

Also verify BMM/CIS plugin invocations inserted in `workflows/business-innovation/bi-m2/`, `bi-m4/`, and `workflows/problem-structuring/steps-c/step-04-deliver.md` — confirm they match actual `bmad-method-lifecycle:*` and `bmad-pro-skills:*` skill names.

### 3. Agent activation no-op stubs may leave placeholders unsubstituted

Phase 4 cleanup replaced each agent's "load config" activation step with a stub: `"No runtime config load. Path variables resolved at install time."` This changes agent startup behavior — if any agent menu handler or workflow step still references `{user_name}`, `{user_language}`, `{output_folder}`, or similar config-sourced variables, they will now appear unsubstituted at runtime.

Action: `grep -rn "{user_name}\|{user_language}\|{user_skill_level}\|{communication_language}" "3. Resources/rbtv"` — for each match, either delete the reference or replace with literal/generic language. Verify during the smoke test that agent responses don't contain raw `{...}` placeholders.

### 4. Admin docs out of sync with standalone reality

These files still contain BMAD-mirror references, `{bmad_rbtv}`, `{bmad_core}`, `_bmad/` paths — excluded from Phase 4 cleanup under the "will be rewritten" exception:

- `admin/CLAUDE.md`
- `workflows/component-creation/data/CLAUDE.md`
- `workflows/component-creation/data/bmad-architecture.md`

Not executable, so not risky. But actively misleading for anyone reading them. Schedule a docs pass to rewrite against the standalone architecture (or delete if superseded by `README.md` + `rules/source-of-truth.md`).

### 6. Workflow location is inconsistent — review architecture

The plan split workflows between two locations based on ownership:

- **Agent-nested** (`agents/<agent>/workflows/<name>/`): doc-compound-learning, doc-context-handoff, add-prompting-knowledge (Ana); problem-structuring, problem-structuring-lite, prompting-assistance, ai-web-project (DomCobb); create-component (Fernando); writing (George Orwell); business-innovation (Paul)
- **Root-level** (`workflows/<name>/`): planning, meeting-summarizer, pitch, product-discovery, design-extraction, output-routing, _shared

The rule (per plan D8) was "agent-exclusive workflows nest under their agent; shared workflows stay at top". But in practice:

- `pitch/` is shared between Leo and Roelof — fine at root
- `product-discovery/` is only invoked via `/rbtv-product-discovery` (skill-triggered, no persona) — why is it at root?
- `design-extraction/` and `meeting-summarizer/` — same pattern
- Paul's `business-innovation/` is nested, but is also the ONLY workflow Paul has — arguably no different from `product-discovery` having no persona

Result: two conventions coexist, and it's not obvious why a new workflow would go to one vs. the other. Creates cognitive load for Fernando (component creator) and for anyone editing the tree.

Action: review and decide one of:
- **(a) Flatten**: move all agent-nested workflows back to root `workflows/`, accept that agents "own" workflows only by reference in their menus
- **(b) Nest more**: move skill-triggered root workflows under a synthetic agent dir (e.g., `agents/_shared/workflows/`), or under the primary persona that invokes them
- **(c) Document the current split clearly**: add a rule in `rules/source-of-truth.md` or `workflows/component-creation/data/component-patterns.md` that states the criterion (e.g., "nest if the workflow is only invoked through one agent's persona; root if skill-triggered or cross-agent")

Keep in mind any choice affects `/rbtv-create-component`'s default location logic.

### 5. Smoke test skipped (plan Task 38)

Loaders compile and install cleanly, but end-to-end behavior was NOT verified in a fresh Claude Code session. Run the smoke test before relying on RBTV for real work:

1. Fresh Claude Code session at vault root
2. `/rbtv-domcobb` — should load DomCobb's persona + menu
3. `/rbtv-client-pitch` — should load Leo + pitch workflow
4. `/rbtv-meeting-summarizer` — should load the workflow (verifies Task 18a transformation)
5. `"dispatch the rbtv-web-research subagent to research X"` — should invoke Task tool with `rbtv-web-research` subagent_type

Any path-resolution error means baked `rbtv_path` is wrong (check `generator.py:_resolve_bake_value` or the installed SKILL.md content).
