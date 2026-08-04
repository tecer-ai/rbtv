# `claude-acct` — switch the `claude` CLI between Claude accounts

One command to move the `claude` CLI from one Claude subscription to another **without
re-logging-in**, so agents keep calling the plain `claude` binary. No wrapper command, no
`CLAUDE_CONFIG_DIR`, no per-account harness. An orchestration-module CLI: `python3`, stdlib only,
no install step beyond a symlink.

The use case is plan-limit rotation across several accounts whose weekly windows reset on
different days: burn one, `use` the next, keep working.

```bash
claude-acct ls                  # slots — * marks the active one, with each login's expiry
claude-acct add <name>          # snapshot the CURRENT login into a slot
claude-acct use <name>          # activate a slot
claude-acct rm <name> --force   # delete a slot (costs that account a re-login)
```

## Install

```bash
ln -s "$(pwd)/orchestration/cli/claude-acct/claude_acct.py" ~/.local/bin/claude-acct
```

Run from the rbtv repo root. The CLI resolves its workspace by walking up from its own real path
to the nearest `rbtv.json`, so the symlink works from any cwd; `RBTV_WORKSPACE` overrides.

## Adding an account

There are no tokens to copy by hand:

```bash
claude /login          # authenticate the account normally
claude-acct add work   # captures whatever is now live
```

## What a slot is

The Claude CLI keeps a login in two places, and both have to move together:

| Source | What it holds |
|---|---|
| `~/.claude/.credentials.json` | the OAuth blob — access token, refresh token, expiries, scopes, subscription tier |
| `~/.claude.json` → `oauthAccount` key | the identity — email, account uuid, org uuid, rate-limit tier |

A slot is a JSON file holding exactly those two, at `{workspace}/.rbtv/env/claude-accts/<name>.json`,
mode `600`. **`.rbtv/env/` is gitignored** — these are real credentials and must never be committed.
Everything else in `~/.claude.json` (project history, settings) is left untouched by `use`.

## Three design points, each paid for by a bug

**Slots are files, not a static `.env`.** Tokens rotate: the access token lasts ~8h and the CLI
rewrites the credential file on every refresh, rolling the refresh token forward to a ~4-week
horizon. A token pasted into an env file is stale within a day. `use` therefore writes the *live*
credentials back into the outgoing slot before swapping the new one in.

**The active slot is derived, never recorded.** An earlier version kept a `.current` marker file;
it drifted out of sync with the real credential store within an hour of existing. The account uuid
in `~/.claude.json` already answers "which account is live" — so `active()` matches that uuid
against the slots and there is no second source of truth to go wrong.

**Two refusals guard the one irreversible act.** A slot is usually the *only* surviving copy of an
account's refresh token, so `use` refuses when the live login matches no slot (it would be
overwritten and lost), and `rm` refuses without `--force`. Both cost a `claude /login` to undo.

## What it does NOT do

**Switching is between sessions.** A running `claude` process holds its token in memory: it will
not pick up a swap, and on its next refresh it writes its own token back over the slot just
activated. Switch, then start new sessions. Mid-run switching is not achievable from outside the
process.
