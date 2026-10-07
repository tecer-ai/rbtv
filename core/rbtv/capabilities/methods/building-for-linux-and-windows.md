# Building for Linux and Windows

Make a change to code, a tool, a test or an installer-scanned file run on both Linux and Windows. The repository's `CLAUDE.md` states which components must run on both and the one exception; this page gives the rules that make a change do so. Each rule records a defect that has happened.

## Apply the rules

1. **Text encoding is explicit.** Every text read and write passes `encoding="utf-8"`. Windows defaults to cp1252 and garbles any non-ASCII byte (`—` becomes `â€”`).
2. **Line endings are CRLF-tolerant.** A Windows checkout (`core.autocrlf`) delivers `\r\n`. Parse with `\r?\n`, never `startswith("---\n")` alone. Decide "unchanged" by comparing the exact bytes you would write, not decoded text.
3. **A tool's CLI runs on both systems.** The CLI that a [tool record](../glossary/tool-json.md)'s `entry` names starts with a shebang line and is committed executable (git mode `100755`); Linux refuses a CLI without both (`path-not-runnable`). Git on Windows records no executable bit, so a CLI created or moved there is committed as mode `100644`. Mark each new or moved CLI with `git update-index --chmod=+x <file>` and commit that staged change from the index: `git commit -- <paths>` re-reads the files and silently drops it. Windows picks the interpreter for its `.cmd` launcher from the shebang or the `.py`, `.js` or `.sh` extension, and refuses the install without one.
4. **No POSIX-only assumptions.** Execute bits (`os.access X_OK` is always true on Windows), symlinks, `/tmp` and shell tools exist on Linux only. Guard with `os.name` and give Windows its own path, or skip a POSIX-only selftest arm with `ctx.skip`, naming why.
5. **Windows file attributes.** Re-creating a Hidden or System file fails with a misleading `PermissionError`. Rewrite the file in place, as the `write_file` function in `core/rbtv/capabilities/tools/rbtv/lib/fsio.py` does.
6. **`~/.rbtv/` is the rbtv home folder.** The [rbtv home folder](../glossary/rbtv-home-folder.md) is present on every machine and is never an installation marker. Code that walks up to find an installation root skips the home folder unless it holds a real install record (`.rbtv/config/install.json`).
7. **File and folder names are Windows-valid.** A name holds none of `: * ? " < > | \`, ends with neither a dot nor a space, and is not a reserved device name (`CON`, `NUL`, `COM1`…). Code that builds a name from a timestamp or user text sanitizes it.

## Verify on both systems

Run the change on Linux and on Windows. On a Windows machine, WSL (Windows Subsystem for Linux, `wsl -d <distro>`) gives a real Linux run: clone the repository inside WSL rather than running over `/mnt/c`, so line endings and the home folder are Linux's.

The rbtv selftest (`core/rbtv/capabilities/tools/rbtv/install.py selftest`) must pass on both systems before a change to rbtv's install code is committed. Its check D3 fails on any file with a `#!` first line stored without the executable bit.

When only one system is available, apply every rule above and name in the done report the system the change was verified on. Do not report a result for the other one.
