You are Kimi, a code executor. Do EXACTLY what this file says. Read nothing else. Inline content below is the full and only context.

ORCHESTRATOR ADDENDUM (binding):
1) If a PRODUCT bug blocks any test from passing, do NOT modify product files — write the failing evidence into the evidence file under a BLOCKED section and finish.
2) NEVER create files at the workspace root; any scratch goes in the OS tempdir.
3) Write ALL run output as evidence into the files this task specifies — your final chat message is not read.

Edit-anchoring rule: locate by exact strings, NEVER line numbers.

# PB-T5 — Re-vendor tool `install-engine.py`

## Objective
Create the stdlib-only re-vendor tool that copies the engine into a target library and syncs the `engine_version` stamp. This is the documented re-vendor command (convention-spec §1.1) and D6-S4.

## FILE ALLOWLIST
- ✚ create `html/slide-library/engine/install-engine.py`
- ✗ nothing else.

## Contract (quotes you implement)
> convention-spec §1.1: "the library's `library.json` records `engine_version` and the engine stamps the same version internally ... The convention provides a documented re-vendor command ... that copies the central engine over the library's copy and bumps the stamp."
> build-spec S-A15: "`python install-engine.py --library {path}` copies `engine/assemble.py` over `{library}/assemble.py` AND syncs `{library}/library.json`'s `engine_version` to the engine's `ENGINE_VERSION`."

## Behavior
- CLI: `argparse`, one required `--library PATH`.
- Resolve the engine source as a sibling of this script: `ENGINE_SRC = Path(__file__).resolve().parent / "assemble.py"`. If absent → print an error to stderr and exit 1.
- The target library is the `--library` path. If `{library}/library.json` does not exist → error + exit 1.
- Read `ENGINE_VERSION` from the engine source. Acceptable methods: import the engine via `importlib.util.spec_from_file_location` and read `m.ENGINE_VERSION`, OR regex the source for `ENGINE_VERSION = "..."`. Prefer the import.
- Copy `ENGINE_SRC` over `{library}/assemble.py` (`shutil.copy2`).
- Load `{library}/library.json` (stdlib `json`), set `engine_version` to the engine's `ENGINE_VERSION`, write it back (a simple `json.load` → set key → `json.dump(..., indent=2)` is fine; preserving original key order is NOT required).
- Print two confirmation lines: the copy (`copied engine -> {target}`) and the stamp bump (`engine_version: {old} -> {new}`). Exit 0.

## Acceptance criteria (self-verifiable, OS tempdir)
1. `python html/slide-library/engine/install-engine.py --help` exits 0.
2. Make a temp dir with a minimal `library.json` (`{"convention_version":"1.0","engine_version":"0.9","name":"t","default_lang":"en","sections":["a"],"extra_asset_root":null}`) and an empty `assemble.py`. Run `install-engine.py --library {tmp}`. Assert: `{tmp}/assemble.py` byte-equals `html/slide-library/engine/assemble.py`; reloading `{tmp}/library.json` shows `engine_version` == the engine's `ENGINE_VERSION` (read the engine the same way the tool does).
3. Run against a temp dir with NO `library.json` → exit code 1.

## Evidence file
Write to `html/hypresent/docs/verification/prez-v1/install-engine-result.md`: the 3 probe results + `git status --porcelain html/slide-library/engine/install-engine.py`.

DONE means: the tool exists, 3 probes pass, evidence written. Failure → BLOCKED + stop.
