# Models

## Purpose

Per-model CLI invocation skills — one installable skill per external model CLI (Kimi, Codex, Manus; future models join the same pattern), each teaching agents how to invoke and orchestrate that model as a worker. A separate module because selective install is a hard requirement: no Kimi on the machine → don't install the Kimi skill.

## Components

**Superseded by D18 (orchestration build).** Models are no longer separate skills: they are JIT **doc packages** that fold into the orchestration module at `orchestration/models/{model}/` (manifest + rendered manual + mirror config), loaded by the `rbtv-orchestrating` skill and selected per-model at install. The first real package — **`orchestration/models/kimi/`** (the validated bounded-code executor, carrying the runtime Kimi contract the M3 mandate needed) — has landed there. This `models.md` module file is retired INTO `modules/orchestration.md` at the docs-coherence pass (p4-11); until then it stands as the pointer to the new home.

## Linkage

See `modules/orchestration.md` § Components → `rbtv-orchestrating` → Model packages (`models/`) for the manifest schema, render machinery, mirror engine, and the per-model packages as they land.
