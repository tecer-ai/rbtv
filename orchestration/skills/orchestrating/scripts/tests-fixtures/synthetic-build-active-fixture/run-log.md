# Run Log — demo-pipeline-build

> Synthetic test fixture. Append-only audit log.

---

## Run Configuration

- **Run mode:** end-to-end
- **Spine location:** ./

---

## Event Log

> Append a row when a dispatch goes out and when its result comes back.

| Timestamp | Event | Task / Batch | Worker | Outcome |
|-----------|-------|--------------|--------|---------|
| 2026-01-01T00:00Z | dispatch | intake | conductor | Placeholder intake event one |
| 2026-01-01T00:05Z | return | intake | conductor | Placeholder intake event two |

---

## Exit Scorecard

> Filled at run end — a second 5-column table that must never receive Event Log appends.

| Timestamp | Event | Task | Worker | Detail |
|-----------|-------|------|--------|--------|
| 2026-01-01T01:00Z | close | run-close | conductor | Placeholder close event |
