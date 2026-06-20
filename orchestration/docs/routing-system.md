# Model Routing System — Developer Reference

> **Scope.** This document explains how the deterministic router *works* — the mechanism, the file layout, how to run its tests, and how to add a model. The per-model capability *values* (each variant's reasoning/coding/cost integers, prices, evidence) live in [`routing-matrix-reference.md`](./routing-matrix-reference.md); the field definitions live in [`../models/manifest-schema.md`](../models/manifest-schema.md). This doc does not restate either.
>
> **Authority.** The routing *card* (`orchestration/skills/orchestrating/cards/routing.md` §2a) is the algorithm authority; `orchestration/models/route.py` is the executable selector the card and the planner both call. On any script-vs-card divergence the card text wins and a defect is filed against the script.

---

## 1. What the router is

A stdlib-only Python selector that maps a **task profile** to a deterministic worker pick:

```
python orchestration/models/route.py <profile.json>          # from repo root
python orchestration/models/route.py <profile.json> --explain # + filter/rank trace
```

It returns one of three verdicts:

| Verdict | Meaning |
|---------|---------|
| `route` | A `(model, variant, carrier)` worker was selected (plus an `effort` label for multi-mode CLI families). |
| `self_execute` | The profile set `self_execute` — the conductor does it in-session, no dispatch. |
| `halt_seam` | An unresolved decision (unset `stakes`, a `cross_strategy` fork) must be taken to the owner before routing. |

Error verdicts (`malformed_profile`, `no_models`, `no_available_variants`, `zero_candidates`) carry a `details` string.

The same script is called at **plan time** (the planner pins each task's executor) and at **run time** (the conductor routes), so plan-time and run-time picks can never disagree.

---

## 2. The selection flow — GATE → RANK → PIN

`route()` runs these stages in order. The three headline stages are **GATE → RANK → PIN**; the surrounding steps prepare and finish the pipeline.

| # | Stage | Function | What it does |
|---|-------|----------|--------------|
| 0 | Enumerate | `_enumerate_models()` | Walk `orchestration/models/{model}/manifest.yaml`, keep only **elected** packages/variants (§7), skip infra dirs (`_api`, `_fixture`, `mirror`) and malformed manifests. |
| 1 | Scope | `_scope_eligible_set()` | The **boundedness master cut** — see §3. Restricts the candidate set by how fully the task is specified. |
| 2 | Plan caps | `_apply_plan_caps()` | Lower each variant's `context_window` to the per-deployment cap (§8). |
| 3 | Availability | `_is_variant_available()` | Drop variants flagged `available: false`, or whose API key is absent (OS env, then the `env_file` in `rbtv.json`). |
| 4 | **GATE** | `_filter()` | Hard pass/fail on every routing requirement (§3). |
| 5 | Haiku guard | `_exclude_haiku()` | Drop `haiku` variants before ranking unless the profile sets `delegation_map_allows_haiku: true`. |
| 6 | **RANK** | `_rank()` | Cost-ascending total order over the survivors (§4). |
| 7 | **PIN / stakes** | `_apply_pins_and_stakes()` | Raise the pick to a pinned-role floor and apply stakes tier-up (§5). Never lowers. |
| 8 | Effort | `_resolve_effort()` | Set the effort label (`low`/`medium`/`high`/`max`) from the chosen variant's `reasoning_modes.depths` and the task's boundedness. CLI carriers only; a no-op on single-mode workers. |

A **footprint fallback** (`_apply_footprint_fallback()`) fires between GATE and the zero-candidates error when the profile carries a `known_input_size` and no worker's capped window holds it: it re-runs every non-window gate over the full roster and picks the largest-window non-haiku survivor, still raised to any pinned floor.

---

## 3. GATE — the boundedness cut, floors, and role-eligibility

### Boundedness master cut

`boundedness` is the first thing the router reads. It both scopes the candidate set and sets the reasoning floor and effort. The three bands:

| Band | Scope (`_scope_eligible_set`) | Reasoning floor | Coding floor | Effort |
|------|-------------------------------|:---------------:|:------------:|--------|
| `fully-bounded` | all eligible variants | 1 | 1 | low |
| `partially-bounded` | Claude mid-tier and up (reasoning ≥ 6) | 6 | 4 | medium |
| `unbounded` | Claude top-tier only (reasoning ≥ 7) | 7 | 5 | high / max |

Floors are byte-for-byte integer comparisons against the 1–7 axes — there is no value-lookup table. Constants: `REASONING_FLOOR_BY_BAND`, `CODING_FLOOR_BY_BAND`.

### The 1–7 axes

`reasoning`, `coding`, and `cost` are comparable integers 1–7, re-derived from one external methodology (the Artificial Analysis leaderboard) so they do not rot:

- **reasoning / coding** — 1 = weakest, 7 = strongest. Used as `score ≥ floor` at GATE and as the capability tiebreak at RANK.
- **cost** — 1 = cheapest, 7 = priciest. The primary RANK key, **ascending**, so the cheapest-capable worker wins; the priciest bin `7` ranks last and is never auto-picked on a cost tie.

### Other hard gates (`_filter`)

A variant is dropped if it fails any of: reasoning floor · coding floor (code leaves only) · `context_window ≥` the task size (after the plan cap) · `web_access` when the task needs web · **`routable_for` allows this leaf**.

### Role-eligibility is independent of the coding score

`routable_for` is an allow-list over the closed role vocabulary `bounded-code · unbounded-code · reasoning · web-research · text-synthesis · other`:

- **Absent or empty** → eligible for every leaf (back-compat default).
- **Present** → eligible only for the listed roles.
- **Code-eligibility rule:** the two code roles (`bounded-code`, `unbounded-code`) are gated on `routable_for` *membership*, not on the coding integer. A non-executor (e.g. an API chat worker) may carry an honest coding score of 3–4 yet never receive a code leaf, because its `routable_for` omits the code roles. An honest coding score never re-enables an ineligible code route.
- An unknown role string is treated as not-matching — never a crash.

When a task routes via the `other` catch-all role, the router records the task's instructions/arguments (`_build_other_routing_audit()`) so under-served task types surface for promotion to a first-class role.

---

## 4. RANK — cost-ascending total order

`_rank()` sorts survivors by this key (all ascending):

1. `cost` (1–7, cheapest first)
2. `evidence_status` (`validated` before `probe-pending`)
3. capability — reasoning on text leaves, coding on code leaves (higher first)
4. carrier preference — Agent-tool Claude before the CLI-process Claude carrier
5. model name, then variant name (final deterministic tiebreak)

Because cost is the primary key, two code-task survivors tied on cost are ordered directly by their `coding` integer — there is no separate sub-rank step.

---

## 5. PIN — role floors, debug floor, stakes, empty-pipeline fallback

Pins raise the pick after ranking; they never lower it. Floors are defined in `_PINNED_FLOORS` and applied by `_apply_pinned_role_floor()`:

| Pinned role | Floor |
|-------------|-------|
| `reviewer` | ≥ executor reasoning + 1, floor Sonnet (reasoning 6), never Haiku. `reviews_external_cli_code: true` forces Opus. |
| `debug` | any code-eligible executor with reasoning ≥ 7. |
| `commit` | Agent-tool Claude Sonnet; if no Claude is available, the strongest-reasoner across all elected packages (excluding Haiku), cost ignored. |

**Stakes tier-up** (`_apply_stakes_tier_up`): a profile with `stakes_tier: tier_up` raises the boundedness band one level and re-resolves (re-scope, re-filter, re-rank) over the full enumeration.

**Empty-pipeline fallback:** when the band-scoped pipeline yields zero candidates but a `pinned_role` is set, the pin's own floor computation runs over the *full pre-scope* roster before returning the error — so a pinned role (e.g. a reviewer) can still be filled when the scoped set came up empty.

---

## 6. Manifest schema — the data interface

`orchestration/models/manifest-schema.md` is the **single source of truth** for the field list and the 1–7 vocabulary; `manifest-template.yaml` is the fill-in skeleton. `route.py`, every package manifest, `test_route.py`, the routing card, and the matrix reference all comply with it.

A package `manifest.yaml` carries package-level keys (`model`, `display`, `evidence_status`, optional `permission_rules`) and a `variants` list — routing always routes on `(model, variant)` pairs, never bare model names. Each variant carries the routing inputs (`reasoning`, `coding`, `cost`, `context_window`, `max_output`, `web_access`, optional `routable_for`, optional `reasoning_modes`, …) plus dispatch and metadata fields. Every required field must hold an evidence-traceable value — no placeholders.

---

## 7. Package layout & election

```
orchestration/models/
  {model}/
    manifest.yaml   # capability + routing inputs (the only routing source)
    delta.md        # model-specific render source (see §8)
    manual.md       # GENERATED dispatch manual — never hand-edit
  manifest-schema.md / manifest-template.yaml   # the schema + skeleton
  model-plans-schema.md / model-plans-example.yaml
  route.py / test_route.py / render-manuals.py
  _api/ _fixture/ mirror/                        # infra dirs — never enumerated
```

**Election is authoritative.** `route.py` enumerates only the packages listed in `rbtv.json` → `model_packages`, and (for a configurable package such as a multi-backend CLI) only the backends listed in `model_variants`. A package or backend absent from those lists is skipped at enumeration. When the lists are absent (e.g. a `--models-dir` override) no election filter applies.

The `<!-- ORCH:AVAILABILITY:BEGIN/END -->` block in `orchestration/skills/orchestrating/core-protocol.md` is an installer-written **recall surface only** (last-install-wins) — it tells the skill what is routable; it is not a routing input. `route.py` reads election from `rbtv.json`, not from that block.

---

## 8. Plan-size context caps

A deployment can cap a model's usable context below its true ceiling (e.g. a subscription tier). The cap file is **cap-only** — it carries `context_window` per model and nothing else (cost stays board-derived in the manifests).

- `rbtv.json` → `model_plans_file` points at the cap file (shape and fields: `model-plans-schema.md`; example: `model-plans-example.yaml`).
- `_apply_plan_caps()` sets each variant's effective window to `min(manifest context_window, plan cap)` — downward only.
- The file is never required: if the pointer is absent or the file is unreadable/unparseable, routing proceeds on the manifest windows unchanged.

---

## 9. Render pipeline — manuals are generated

A model's dispatch **manual** (`manual.md`) is composed by `render-manuals.py` from two sources — never hand-written:

- the shared wrapper template `orchestration/skills/orchestrating/cards/dispatch-wrapper.md` (the generic dispatch contract + render seams), and
- the model's `delta.md` (model-specific content; every delta must supply the `invocation` section).

Composition uses an HTML-comment marker grammar (`RENDER:BEGIN/END`, `RENDER:INSERT`, `RENDER:DELTA`). Rendering is deterministic (write-if-changed, no timestamps), so re-rendering unchanged inputs is byte-identical.

```
python orchestration/models/render-manuals.py            # regenerate all manuals
python orchestration/models/render-manuals.py --check     # report drift, write nothing; exit 1 if any manual is stale
```

`--check` must exit 0 (zero drift). To change a manual, edit the wrapper template (cross-model behavior) or the model's `delta.md` (model-specific behavior), then re-render — never edit `manual.md` directly.

---

## 10. Running the tests

**Canonical command (from the repo root):**

```
python -m pytest orchestration/models/test_route.py
```

**Gotcha — `python orchestration/models/test_route.py` collects ZERO tests** and exits 0 with no output. The suite's tests take pytest fixtures (`tmp_path`) and the file has no `if __name__ == "__main__"` block, so running it as a plain script merely loads the test classes without invoking anything. Always run it through `pytest`. (This silent no-op is the gap this document exists to close.)

The suite covers the reference profiles (fully/partially/unbounded), the boundedness keystone, determinism, API-key availability, plan caps (parse, apply, graceful skip), halt seams, self-execute, the `--explain` trace, failure modes, stakes/pinned-role floors, the Haiku guard, and a live-corpus enumeration.

---

## 11. Add or migrate a model

1. **Elect** the package: add it to `model_packages` in `rbtv.json` (run the installer's picker, or pass `--model-packages …`). For a multi-backend package, also set its `model_variants` subset.
2. **Author** `orchestration/models/{model}/manifest.yaml` from `manifest-template.yaml`, filling every required field with an evidence-traceable value per `manifest-schema.md`. Set the 1–7 axes from the external methodology used by all other models (keep them comparable).
3. **Write** `delta.md` with the model's dispatch specifics, including the required `invocation` section.
4. **Render** the manual: `python orchestration/models/render-manuals.py`, then confirm `--check` exits 0.
5. **Add/extend tests** in `test_route.py` for any new routing behavior.
6. **Run the suite:** `python -m pytest orchestration/models/test_route.py` — all green.
7. **Keep docs in sync** (repo hard rule): update `modules/orchestration.md`, the matrix reference if a routable variant changed, and `admin/install/module-manifest.json` if a package was added/removed/renamed.
