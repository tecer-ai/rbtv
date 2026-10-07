# rbtv

`rbtv` is the rbtv command-line interface: it scans the repository and an installation's mirror, validates each record, and writes the files each harness receives into a target folder. It also manages an installation's agents (`rbtv agent`) and the provider accounts of a machine (`rbtv providers`). `rbtv -h` and each verb's `-h` own the grammar, options and exit codes.

The program is `install.py` in this folder: a small entry point, one module per responsibility in `lib/`, `discovery.py` beside the entry point, and the checks in `selftest/`, one module per subject.

## Read for this work

| File | CONTAINS | PURPOSE | ALWAYS LOAD WHEN |
|---|---|---|---|
| [rbtv CLI](../../glossary/rbtv-cli.md) | What the scan recognizes, what is generated for each harness, target and placement, results and refresh | Validate and deliver a source change | creating, moving or converting a scanned file, or reading what a command reported |
| [Provider accounts](documentation/providers.md) | The `rbtv providers` verbs, where a saved login lives and the providers file | Save, switch and read provider accounts | listing or switching provider logins, reading usage limits, or adding a supported provider |
| [Installer design decisions](documentation/design-decisions.md) | The decisions in force for the installer, each with its reason | Change the installer without undoing a settled choice | changing `install.py`, `lib/`, `discovery.py` or `selftest/` |

## Self-check

Run from the repository root, on Linux and on Windows, before committing a change to the installer:

```
python3 core/rbtv/capabilities/tools/rbtv/install.py selftest     # -> selftest: PASS
```
