# 20260831-i-caged-local-did-not-survive-th — Caged ~/.local did not survive the next sitting

kind: issue
component: supervisor
date: 2026-08-31
commit: 867b4d31
deployed: no
pin: ignite/supervisor/spawn/probes/probe-local-persist.js

## Observed
Daemon-lane caged seats reinstalled user-site Python packages on every sitting (~15s; pytest was the measured case). A `pip3 install --user` in sitting 1 was gone in sitting 2 of the same seat. Seeded as redesign-continue-1 task 119 from the 2026-08-23 scaffolding-blockers meet. Repo HEAD at the fix; the running daemon still boots the deploy worktree and does not yet carry this bind.

## Mechanism
`bwrap.js` mounts a throwaway tmpfs over HOME before any punch-through. `pip --user` writes `~/.local/lib/...` on that tmpfs, so the tree dies with the sitting. `resolveLocalBinGrant` only ro-binds the host `~/.local/bin` (PATH + CLI names) when `local-bin: true`; it never mounted a writable `~/.local` tree. Envelope `composeCageFor` had no persist bind either. The host `~/.local/bin` ro-bind is not this fix — that is the pre-existing grant and it does not keep site-packages.

## Attempts
First attempt held — checked: `d487c072` (module-directory symlinks, unrelated); `git log -S'localBin'` / `.local` on spawn.js and bwrap.js (uncaged PATH `af326d61`, D56/D74 refusal shims `7f6eaf3e`, no persist mount); spawn-profiles.yaml `local-bin` comment still documents the host bin ro-bind only.

## Fix
Each caged seat gets a durable store at `<seatDir>/.user-local`, mkdir'd at compose, `--bind` onto `$HOME/.local` after the HOME tmpfs (last-wins punch-through). Sitting 2 of the same seat sees the same user-site tree with no pip. Host-provision of known deps (pytest via apt/manifest) lost: seats install ad-hoc packages, and a static list does not stop the next sitting needing a different one. A per-goal read-only snapshot lost: sitting 1 could not `pip install --user` into it, which is the measured act. The host's full `~/.local` is never bound writable — one seat's pip must not mutate the owner's env.

## Consequences
Uncaged staff seats are unchanged (real HOME, early return). `local-bin: true` still prepends the host bin on PATH; persist occupies `~/.local` so that PATH entry is the seat store's `bin/` plus whatever host names still resolve. On this Debian box `pip --user` is PEP 668-blocked without `--break-system-packages`; that is the install command, not a second persist mechanism. spawn.js remains a pre-existing monolith (this change added persist beside `resolveLocalBinGrant`, did not split the file).

## Verification
`probe-local-persist` — sitting 1 `pip install --user --break-system-packages` a dummy package, sitting 2 of the same fixture seat imports with no pip; host `~/.local` untouched. Red-first: HEAD spawn.js in a scratch worktree failed legs 1/3/4 (sitting 1 import still worked on tmpfs; sitting 2 ModuleNotFoundError); copying the fix spawn.js passed. Sibling probes `probe-envelope-walls`, `probe-exposed-cli-secrets`, `probe-seat-cage` PASS. Not deployed.

## ATTENTION
- Do not bind the host `~/.local` writable into cages — persist lives under the seat folder and is mounted at `~/.local`.
- HOME tmpfs is laid down in bwrap.js before seatBinds; the persist `--bind` must stay on the composeCageFor flag list so it punches through. Reordering bwrap.js tmpfs after binds would shadow it.
- Debian PEP 668 refuses bare `pip install --user`; live verify needs `--break-system-packages` (or equivalent) or the import proof never installs.
- This bind is inert until `rbtv ignite daemon deploy` — the daemon runs the deploy worktree, not this commit.
