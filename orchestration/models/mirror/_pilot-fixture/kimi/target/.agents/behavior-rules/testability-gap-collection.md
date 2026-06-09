# Testability-Gap Collection

Companion to `rbtv-done-gate` / `rbtv-build-for-agent-testability`: auto-captures agent-testability gaps for future rule authoring. Vault-only — NEVER enters RBTV. `rbtv-build-for-agent-testability` shipped 2026-06-08 (build-side classes) and the done-gate fidelity floor absorbed the saturated craft lessons; collection CONTINUES for unhoused/new classes. Retires when the registry's recurring classes are all housed in a shipped rule — then delete this rule, keep the registry as evidence.

## Gate

When a done-gate evidence sheet is finalized in a **vault-rooted** session with a row marked `unexercisable` or `failed`, OR a real-input friction event occurs (tooling can't drive the app, no entry point, manual setup, flaky automation), append ONE row to `1-projects/rbtv-evolution/coding/testability-gap-registry.md`:

`date (last occurrence) | project | feature | blocker | workaround | count`

- **Dedup:** same gap + same project → bump `count` and `date` on the existing row; NEVER duplicate.
- **Specific, not generic:** name the exact feature and exact blocker ("browser automation is hard" is noise).
- Append at the moment of friction — end-of-task memory loses gaps. No qualifying row and no friction = no-op.
