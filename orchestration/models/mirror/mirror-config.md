# Mirror-config convention

The per-model config the mirror engine (`mirror.py`) reads to generate a model's
per-workspace guidance file. Each model package that needs a guidance file ships
one at `orchestration/models/<model>/mirror-config.yaml`; the kimi, codex,
claude-code-cli, and qwen packages fill this in at their package-build tasks
(p3-4/p3-5/p3-7/p3-9). A package whose worker loads NO workspace guidance file
ships no mirror-config (and its manifest omits `guidance_file`).

The engine consumes this config; `mirror.py`'s module docstring is the engine
contract. This file is the config schema.

## Why a config seam

`mirror.py` carries the generic, validated mechanics (banner bake, idempotent
write-if-changed, staleness `--check`). WHAT to generate — the guidance filename
and which source it mirrors from — is per-model. The config is that seam: the
engine ships once; each package declares its own values here. This is the
generalization of the vault-local `.user/runtime/scripts/{kimi,codex}-mirror.py`,
whose model-specific facts were hardcoded.

## Schema

A mirror-config is a flat `key: value` YAML file (no nesting, no lists — the
engine parses this subset with no YAML dependency). Comments (`#`) and blank
lines are allowed; values may be optionally quoted.

| Key | Required | Meaning |
|-----|----------|---------|
| `model` | yes | The package id — matches the folder name `models/<model>/` and the manifest's `model`. Used in error messages and as the config's identity. |
| `guidance_filename` | yes | The guidance file the worker natively loads, emitted at the target workspace root (e.g. `AGENTS.md` for kimi/codex, `CLAUDE.md` for claude-code-cli). MUST match the manifest's `guidance_file.convention`. |
| `source` | yes | Workspace-relative path to the file whose body is mirrored into the guidance file (e.g. `CLAUDE.md`). Resolved against `--target` at run time. Missing source → the engine fails loudly. |
| `banner_label` | yes | Short human label naming the consuming worker, interpolated into the DO-NOT-EDIT banner (e.g. `the Kimi CLI worker`). |

The engine emits: a DO-NOT-EDIT banner (naming `source` and the re-run command)
followed by the `source` file's body, written to `guidance_filename` at the
target root.

## Manifest linkage

The manifest's `guidance_file.mirror_entry` (capability-manifest schema §2) names
this config's entry point. By convention `mirror_entry: <model>-mirror` resolves
to running `mirror.py --config orchestration/models/<model>/mirror-config.yaml`.
The routing card's pre-dispatch guidance-file check (dispatch path) offers to
invoke exactly this when a target workspace lacks the worker's guidance file.

## Example (the test fixture)

`models/_fixture/mirror-config.yaml` is a clearly-marked fixture config that
exercises the engine without a real package. It is kept (not deleted) so the
done-gate cold verifier can re-exercise the create / in-sync / stale paths
against a committed artifact. Safe to delete once two or more real model
mirror-configs exist.
