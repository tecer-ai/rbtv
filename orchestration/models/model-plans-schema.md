# Model Plans Schema

> **Purpose:** Defines the shape of the plan-overlay file pointed to by the `model_plans_file` field in `rbtv.json`. The router script reads this file to apply per-model context-window caps. **Cap-only (D14):** the only per-model field is `context_window`. Cost is board-derived (an integer 1–7) in the model manifests (D11), NOT here — the router never reads cost from this file. Field-count discipline: no speculative fields.

---

## File shape

The file is a YAML list of plan entries. Each entry represents one `(model, plan)` pair.

```yaml
plans:
  - model: <package-id>          # Required. Must match an installed model package folder name
                                 # under orchestration/models/ (e.g. "codex-cli", "claude-code-native").
    plan_name: <string>          # Optional. Human-readable plan/subscription name (e.g. "basic", "pro", "team").
    context_window: <int>        # Optional. Effective context-window cap the plan enforces (tokens).
                                 # When present, the router uses min(manifest context_window, this cap)
                                 # as the effective window for Stage-2 filtering (router spec S4).
                                 # Absent = use the manifest context_window unchanged.
```

The installer fills `context_window` from a per-model plan-size **preset pick-list** (D14) — the owner picks a plan size from a menu, never types a raw token number. A previously-chosen value is re-confirmed (offered as the default) on reinstall, never silently wiped.

**Multi-model clobber warning.** One per-package cap is applied to EVERY variant (router `min(manifest window, cap)`). When a package's variants carry different native windows (e.g. `claude-code-native`: opus 1M, sonnet/haiku 200K), a cap below the largest silently shrinks the bigger variant. The installer therefore WARNS at pick time when a chosen size is below the package's largest native window, naming the clobbered variant(s) — advisory only, the cap is still applied (a genuine uniform subscription ceiling stays legitimate).

## Field inventory (router-consumed)

| Field | Consumed by | Purpose |
|-------|-------------|---------|
| `model` | Router (enumerate + match) | Keys the plan entry to the installed model package; must equal the package's manifest `model:` id |
| `plan_name` | Router (--explain trace) | Human-readable label in the trace |
| `context_window` | Router (S4 effective window) | Caps the manifest's context_window for Stage-2 filtering |

## Cost is not in this file (D14)

Cost is a board-derived integer 1–7 on each variant in the model manifests (D11) — the router reads `cost` from there for gate/rank, NEVER from this plan-overlay file. The retired `cost_usd_per_m_in` / `cost_usd_per_m_out` reference rows are dropped: the router never multiplied them by token counts and never ranked on them, so they carried no routing signal.

## Graceful skip

If `rbtv.json` lacks a `model_plans_file` pointer, or the pointed file is absent/unreadable, the router proceeds with manifest context_window unchanged and applies no caps (router spec S4, behavior rule 13). The plans file is NEVER required for routing to function.
