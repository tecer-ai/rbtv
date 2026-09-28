# Fixture operating scope — m4 unattended-skill probes

This folder is the operating scope the m4 probes run under. Each probe run gets its own copy of
it, so a run's writebacks are observable in isolation and the owner's live vault data is never
involved. Every value here is `EXAMPLE-` prefixed for the same reason.

## Name Glossary

Glossary path: `glossary.md` (in this folder).

## File Routing

| Output type | Destination |
|---|---|
| `meeting-summary` | `destination/{entity}/meetings/{type}/` |
| `therapy-summary` | `destination/EXAMPLE-wellbeing/{year}/encontros/` |

Summary filename: `{date}-{slug}-resumo.md`.
