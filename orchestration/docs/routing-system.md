# Routing — pointer

Historical: the models tree (`orchestration/models/`, including `route.py`, manuals, deltas, `_api`, and `render-manuals.py`) is retired. Live surfaces live in the cast world:

| Surface | What it is |
|---|---|
| `cast route` | Selector. GATE→RANK→PIN over the catalog. Plan-time and run-time both CALL this. |
| `cast route --catalog` | Live roster (add `--json` for the machine-readable view). This is the `--availability` equivalent. |
| `cast` | Conductor dispatch: `cast <harness> <model> <effort> [folder] -p/-f …` |
| `cast api` | API-worker runner (`carrier: api` rows). `cast` refuses to launch those rows. |
| catalog | `.rbtv/mirror/meta/providers/capabilities/cast/` (`catalog.js` + `cast.md`) |

**Algorithm authority** is the routing card: `orchestration/skills/orchestrating/cards/routing.md` §1 / §2a. On any script-vs-card divergence the card text wins and a defect is filed against `cast route`.

**Routable set** = catalog ∩ availability. Availability-now = binary installed per `cast doctor`, plus API-key resolution for `carrier: api` rows. There is no install-time `model_packages` election and no add-a-model walk under a models tree.

Cards and skills CALL `cast`. The rbtv repo keeps no router / dispatch / model-catalog implementation.
