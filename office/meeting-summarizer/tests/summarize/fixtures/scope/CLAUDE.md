# Fixture operating scope — m6 per-meeting-job probes

Each probe run gets its own copy of this folder as the summarizer's working directory, so every
writeback is observable against that copy's own before-state and the owner's live vault is never
involved. Every value here is `EXAMPLE-` prefixed or invented for the same reason.

## Name Glossary

Glossary path: `glossary.md` (in this folder).

## File Routing

The per-meeting job supplies the destination folder and the summary filename on the invocation.
Follow what the invocation names; do not re-derive a destination from this table.

Summary filename: `{date}-{slug}-resumo.md`.
