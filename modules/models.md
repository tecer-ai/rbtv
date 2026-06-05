# Models

## Purpose

Per-model CLI invocation skills — one installable skill per external model CLI (Kimi, Codex, Manus; future models join the same pattern), each teaching agents how to invoke and orchestrate that model as a worker. A separate module because selective install is a hard requirement: no Kimi on the machine → don't install the Kimi skill.

## Components

No components yet. The module is reserved by the locked taxonomy and populated by the models build task in the rbtv-evolution backlog (kimi/codex/manus invocation skills, including the runtime Kimi rules component). The folder structure materializes with the first component.

## Linkage

The planned general orchestration skill (orchestration module) references these per-model skills when installed and degrades gracefully when they are absent.
