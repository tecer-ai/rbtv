---
description: "The providers component — the two CLIs that stand between this workspace and whoever supplies its compute: launch an executor in any harness (`cast`), and manage the accounts the harnesses authenticate with (`acct`)."
---

# providers

Every agent this workspace runs is somebody else's compute, reached through somebody else's
software. This component owns the seam: the two capabilities that let the rest of the system treat
that seam as uniform.

| Capability | Answers |
|---|---|
| `cast` | **How does an executor get launched, and which one?** One headless agent turn in any of three harnesses — claude, codex, opencode — behind one CLI, with one universal 1-5 effort dial. Also `route` (a task profile in, one deterministic `(harness, model, effort, carrier)` verdict out) and `resume`/`sessions` for addressing a launch after the fact. |
| `acct` | **Whose account does it run on, and how much is left?** Provider logins parked in named slots, switched without re-logging-in, plus each account's plan windows and their renew times. |

The pairing is not a convenience. `cast` decides WHICH executor runs; `acct` decides WHOSE
entitlement it burns and reports what remains. Rotating a burnt weekly window and picking a
harness+model for the next launch are the same operational question asked twice, and holding both
here keeps the answer in one place.

## Why this component exists — `PRIN-6`, both halves

`PRIN-6` is agnostic to the **harness** that runs the loop AND to the **provider** that supplies the
model and the entitlement (amended 2026-08-14,
`system-definition/decisions.md#d-prin6-provider-abstraction`). Both are ABSTRACTED and neither is
DECOMPOSED: the system commits to an interface — launch an executor, hold a credential, read a
limit — and to nothing behind it. This component is where that interface is implemented, which is
why a new harness or a new provider is wiring HERE and content changes nowhere.

The corollary is the standing constraint on both tools: knowing more about a provider's internals is
never the fix. When one of them cannot express something, the interface is too narrow — widen it,
rather than teaching the tool a vendor's private shape.

**RELOCATED 2026-08-21 from `meta/providers/` to `core/providers/`** (following `cast`'s own
2026-08-20 move out of this component into `core/sub-agents/`) — see `meta/module.md` § Components for
the tombstone row. It holds no seats and no workflow — a capability-only component, the shape
`web/browse/` already established.

## Entry points

- `cast` — **RELOCATED 2026-08-20 to `core/sub-agents/`** (owner instruction, route-redesign
  spec §8), now a component of its own — its exposure row lives in `core/sub-agents/exposure.csv`.
  There: `component.md` (the manual) +
  `tool/cast.js`, `tool/catalog.js`, `tool/models.csv`, `tool/test_cast.js`, `tool/test_route.js`,
  and the API runner at `tool/api/run.py` + `tool/api/clients/` + `tool/api/tests/`. On PATH as
  `cast`. The catalog is now SPLIT by concern: `tool/catalog.js` holds LAUNCH mechanics (harness-
  native id, effort ladder, auth) for every `mode: cli|api` row, `tool/models.csv` holds the
  ROUTING axes (level, reasoning, coding, cost, web, image), and `cast route` joins the two on
  harness+model. A per-vault whole-file override of the CSV lives at
  `{vault}/.rbtv/config/modules/core/sub-agents/models.csv`. The `api` verb (`cast api <model> …`)
  shells to `tool/api/run.py` for the `mode: api` rows (Google only). After any edit,
  `node tool/test_cast.js` must print `all cast tests passed`, `node tool/test_route.js` must
  print `all route tests passed`, and `python -m pytest tool/api/tests/ -q` must be green.
- `capabilities/acct/` — `acct.md` (the manual) + `tool/acct.py`. On PATH as `acct`.
  `acct --selftest` must exit 0 after any edit.
- `exposure.csv` — `acct` only, as the mandatory first-party tool inventory (`cast`'s row moved
  with it to `core/sub-agents/exposure.csv`).

Each tool orients with its own `doctor` verb: `cast doctor` reports which harness binaries are
installed, which providers are enabled behind them, and what is left on each — by running
`acct doctor` + `acct usage`, which own those answers (the provider half covers every credential
that exists, including the ones reached only through opencode's store). One view, one
implementation; `cast` keeps no second harness list and no second usage reader.

## Credentials never live here

`acct`'s slots are written to `{workspace}/.rbtv/config/acct/<provider>/<name>.json`, mode 600,
gitignored by that directory's own rule — the CMP-1-ruled credential home, resolved by walking up
from the tool's real path to the nearest `rbtv.json`. Nothing under this component holds a
credential, and relocating either tool does not move the store.
