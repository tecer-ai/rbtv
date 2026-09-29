---
description: "Use for owner administration: inspect or switch AI provider accounts and usage, list or install rbtv components, run rbtv selftests, or view and update the rbtv control panel. Assigned to the master agent only."
exposes-cli:
  - core/providers/acct
  - meta/rbtv-cli/rbtv
  - meta/control-panel/rbtv-control-panel
---

# admin

This skill belongs to the master agent. Run the named command's `--help` before choosing flags.

| Request | Tool |
|---|---|
| Inspect provider accounts, usage, or login health; switch an account | `acct` — see `core/providers/capabilities/acct/acct.md` for account-slot behavior |
| Discover modules, components, skills, or rules; install, remove, or diagnose one | `rbtv install` — run `status` for the current target, `list` and `show` to choose a stable name, then `add` or `remove`; use `doctor` for diagnosis |
| Check rbtv mechanics | `rbtv selftest` or `rbtv install selftest` for the installer |
| Inspect or refresh the control panel | `rbtv-control-panel status|update|selftest` |

For another agent, pass `--target <agent-home>` to each installer command. The current agent's `IGNITE_AGENT_HOME` selects its own home. Use `--dry-run` when the change's scope is uncertain. Report the resolved target and what changed.
