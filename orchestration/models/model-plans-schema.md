# Model Plans Schema

> **Purpose:** Defines the shape of the plan-overlay file pointed to by the `model_plans_file` field in `rbtv.json`. The router script (p2-4) reads this file to apply per-model context-window caps and surface reference-only `$/M-token` data. ONLY fields the router spec or the intake budget question consume — field-count discipline (no speculative fields).

---

## File shape

The file is a YAML list of plan entries. Each entry represents one `(model, plan)` pair.

```yaml
plans:
  - model: <package-id>          # Required. Must match an installed model package folder name
                                 # under orchestration/models/ (e.g. "codex", "claude", "qwen").
    plan_name: <string>          # Required. Human-readable plan/subscription name (e.g. "basic", "pro", "team").
    context_window: <int>        # Optional. Effective context-window cap the plan enforces (tokens).
                                 # When present, the router uses min(manifest context_window, this cap)
                                 # as the effective window for Stage-2 filtering (router spec S4).
                                 # Absent = use the manifest context_window unchanged.
    cost_usd_per_m_in: <float>   # Optional. $/M input tokens — reference data ONLY (router spec S5).
                                 # The router surfaces this as passthrough in --explain; NEVER computes spend.
    cost_usd_per_m_out: <float>  # Optional. $/M output tokens — reference data ONLY (router spec S5).
```

## Field inventory (router-consumed)

| Field | Consumed by | Purpose |
|-------|-------------|---------|
| `model` | Router (enumerate + match) | Keys the plan entry to the installed model package |
| `plan_name` | Router (--explain trace) | Human-readable label in the trace |
| `context_window` | Router (S4 effective window) | Caps the manifest's context_window for Stage-2 filtering |
| `cost_usd_per_m_in` | Router (S5 reference passthrough) | Flows into --explain/verdict as human-budget reference |
| `cost_usd_per_m_out` | Router (S5 reference passthrough) | Flows into --explain/verdict as human-budget reference |

## Invariant 6

`cost_usd_per_m_in` and `cost_usd_per_m_out` are **reference-only data**. The router script never multiplies them by token counts, never projects run spend, and never uses them for ranking (ranking is `cost_class` only — router spec S1 Stage 3). Dollar figures pass through the script untouched.

## Graceful skip

If `rbtv.json` lacks a `model_plans_file` pointer, or the pointed file is absent/unreadable, the router proceeds with manifest context_window unchanged and applies no caps (router spec S4, behavior rule 13). The plans file is NEVER required for routing to function.
